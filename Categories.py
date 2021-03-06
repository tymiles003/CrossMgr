import wx
import re
import os
import Utils
import Model
from Undo import undo
import wx.grid			as gridlib
from ReorderableGrid import ReorderableGrid
import wx.lib.masked	as  masked

from GetResults import GetCategoryDetails, UnstartedRaceWrapper
from ExportGrid import ExportGrid

#--------------------------------------------------------------------------------

allName = _('All')

class CategoriesPrintout( wx.Printout ):
	def __init__(self, categories = None):
		wx.Printout.__init__(self)

	def OnBeginDocument(self, start, end):
		return super(CategoriesPrintout, self).OnBeginDocument(start, end)

	def OnEndDocument(self):
		super(CategoriesPrintout, self).OnEndDocument()

	def OnBeginPrinting(self):
		super(CategoriesPrintout, self).OnBeginPrinting()

	def OnEndPrinting(self):
		super(CategoriesPrintout, self).OnEndPrinting()

	def OnPreparePrinting(self):
		super(CategoriesPrintout, self).OnPreparePrinting()

	def HasPage(self, page):
		return page == 1

	def GetPageInfo(self):
		return (1,1,1,1)

	def OnPrintPage(self, page):
		race = Model.race
		if not race:
			return
		
		try:
			externalInfo = race.excelLink.read()
		except:
			externalInfo = {}
		
		GetTranslation = _
		allZeroStarters = True
		with UnstartedRaceWrapper():
			catMap = dict( (c.fullname, c) for c in race.getCategories( startWaveOnly=False ) )
			catDetails = GetCategoryDetails( False )
			catDetailsMap = dict( (cd['name'], cd) for cd in catDetails )
			
			title = u'\n'.join( [_('Categories'), race.name, race.scheduledStart + u' ' + _('Start on') + u' ' + Utils.formatDate(race.date)] )
			colnames = [_('Start Time'), _('Category'), _('Gender'), _('Numbers'), _('Laps'), _('Distance'), _('Starters')]
			
			raceStart = Utils.StrToSeconds( race.scheduledStart + ':00' )
			catData = []
			for catInfo in catDetails:
				c = catMap.get( catInfo['name'], None )
				if not c:
					continue
				
				starters = race.catCount(c)
				if starters:
					allZeroStarters = False
				else:
					starters = ''
				
				laps = catInfo.get( 'laps', '' ) or ''
				raceDistance = catInfo.get( 'raceDistance', '' )
				raceDistanceUnit = catInfo.get( 'distanceUnit', '')
				
				if raceDistance:
					raceDistance = '%.2f' % raceDistance
					
				if c.catType == c.CatWave:
					catStart = Utils.SecondsToStr( raceStart + c.getStartOffsetSecs() )
				elif c.catType == c.CatCustom:
					catStart = Utils.SecondsToStr( raceStart )
				else:
					catStart = ''
					
				catData.append( [
					catStart,
					u' - ' + c.name if c.catType == c.CatComponent else c.name,
					GetTranslation(catInfo.get('gender', 'Open')),
					c.catStr,
					u'{}'.format(laps),
					u' '.join([raceDistance, raceDistanceUnit]) if raceDistance else '',
					u'{}'.format(starters)
				])
		
		if allZeroStarters:
			colnames.remove( _('Starters') )
		data = [[None] * len(catData) for i in xrange(len(colnames))]
		for row in xrange(len(catData)):
			for col in xrange(len(colnames)):
				data[col][row] = catData[row][col]
				
		exportGrid = ExportGrid( title = title, colnames = colnames, data = data )
		exportGrid.leftJustifyCols = { 1, 2, 3 }
		exportGrid.drawToFitDC( self.GetDC() )
		return True

def PrintCategories():
	mainWin = Utils.getMainWin()
	race = Model.race
	if not mainWin or not race:
		return
	
	pdd = wx.PrintDialogData(mainWin.printData)
	pdd.SetAllPages( True )
	pdd.EnableSelection( False )
	pdd.EnablePageNumbers( False )
	pdd.EnableHelp( False )
	pdd.EnablePrintToFile( False )
	
	printer = wx.Printer(pdd)
	printout = CategoriesPrintout()

	if not printer.Print(mainWin, printout, True):
		if printer.GetLastError() == wx.PRINTER_ERROR:
			Utils.MessageOK(self, u'\n\n'.join( [_("There was a printer problem."), _("Check your printer setup.")] ), _("Printer Error"), iconMask=wx.ICON_ERROR)
	else:
		mainWin.printData = wx.PrintData( printer.GetPrintDialogData().GetPrintData() )

	printout.Destroy()	

#--------------------------------------------------------------------------------
class TimeEditor(gridlib.PyGridCellEditor):
	def __init__(self):
		self._tc = None
		self.startValue = '00:00:00'
		gridlib.PyGridCellEditor.__init__(self)
		
	def Create( self, parent, id = wx.ID_ANY, evtHandler = None ):
		self._tc = masked.TimeCtrl( parent, id, style=wx.TE_CENTRE, fmt24hr=True, displaySeconds = True, value = '00:00:00' )
		self.SetControl( self._tc )
		if evtHandler:
			self._tc.PushEventHandler( evtHandler )
	
	def SetSize( self, rect ):
		self._tc.SetDimensions(rect.x, rect.y, rect.width+2, rect.height+2, wx.SIZE_ALLOW_MINUS_ONE )
	
	def BeginEdit( self, row, col, grid ):
		self.startValue = grid.GetTable().GetValue(row, col)
		self._tc.SetValue( self.startValue )
		self._tc.SetFocus()
		
	def EndEdit( self, row, col, grid, value = None ):
		changed = False
		val = self._tc.GetValue()
		if val != self.startValue:
			changed = True
			grid.GetTable().SetValue( row, col, val )
		self.startValue = '00:00:00'
		self._tc.SetValue( self.startValue )
		
	def Reset( self ):
		self._tc.SetValue( self.startValue )
		
	def Clone( self ):
		return TimeEditor()

class CategoryIconRenderer(gridlib.PyGridCellRenderer):
	def __init__( self ):
		self.bitmaps = [
			wx.Bitmap( os.path.join(Utils.getImageFolder(), 'bullhorn_2.png'), wx.BITMAP_TYPE_PNG ),
			wx.Bitmap( os.path.join(Utils.getImageFolder(), 'arrow_right_alt.png'), wx.BITMAP_TYPE_PNG ),
			wx.Bitmap( os.path.join(Utils.getImageFolder(), 'point-of-interest-icon.png'), wx.BITMAP_TYPE_PNG ),
		]
		wMax = hMax = 0
		for b in self.bitmaps:
			w, h = b.GetSize()
			wMax = max( wMax, w )
			hMax = max( hMax, h )
		self.wMax = wMax
		self.hMax = hMax
		gridlib.PyGridCellRenderer.__init__(self)

	def Draw(self, grid, attr, dc, rect, row, col, isSelected):
		value = grid.GetCellValue( row, col+1 ).strip()
		
		if value.endswith( _('Start Wave') ):
			value = 0
		elif value.endswith( _('Component') ):
			value = 1
		else:
			value = 2
		
		dc.SetClippingRect( rect )
		dc.SetBackgroundMode(wx.SOLID)
		dc.SetBrush(wx.WHITE_BRUSH)
		dc.SetPen(wx.TRANSPARENT_PEN)
		dc.DrawRectangleRect(rect)
		
		bitmap = self.bitmaps[value]
		w, h = bitmap.GetSize()
		x = (rect.GetWidth() - w) // 2
		y = (rect.GetHeight() - h) // 2
		dc.DrawBitmap(bitmap, rect.x + x, rect.y + y)
		
		dc.DestroyClippingRegion()

	def GetBestSize(self, grid, attr, dc, row, col):
		return wx.Size(self.wMax, self.hMax)

	def Clone(self):
		return CategoryIconRenderer()
		
#--------------------------------------------------------------------------------
class Categories( wx.Panel ):
	CategoryTypeChoices = [_('Start Wave'),u'    ' + _('Component'),_('Custom')]
	DistanceTypeChoices = [_('Lap'),_('Race')]
	
	def __init__( self, parent, id = wx.ID_ANY ):
		wx.Panel.__init__(self, parent, id)
		
		vs = wx.BoxSizer( wx.VERTICAL )
		
		self.ignoreColour = wx.Colour( 80, 80, 80 )
		self.inactiveColour = wx.Colour( 220, 220, 220 )
		
		border = 4
		flag = wx.ALL
		
		hs = wx.BoxSizer( wx.HORIZONTAL )
		
		self.activateAllButton = wx.Button(self, label=_('&Activate All'), style=wx.BU_EXACTFIT)
		self.Bind( wx.EVT_BUTTON, self.onActivateAll, self.activateAllButton )
		hs.Add( self.activateAllButton, 0, border = border, flag = flag )

		self.deactivateAllButton = wx.Button(self, label=_('&Deactivate All'), style=wx.BU_EXACTFIT)
		self.Bind( wx.EVT_BUTTON, self.onDeactivateAll, self.deactivateAllButton )
		hs.Add( self.deactivateAllButton, 0, border = border, flag = (flag & ~wx.LEFT) )

		hs.AddSpacer( 8 )
		
		self.newCategoryButton = wx.Button(self, label=_('&New Category'), style=wx.BU_EXACTFIT)
		self.Bind( wx.EVT_BUTTON, self.onNewCategory, self.newCategoryButton )
		hs.Add( self.newCategoryButton, 0, border = border, flag = flag )
		
		self.delCategoryButton = wx.Button(self, label=_('&Delete Category'), style=wx.BU_EXACTFIT)
		self.Bind( wx.EVT_BUTTON, self.onDelCategory, self.delCategoryButton )
		hs.Add( self.delCategoryButton, 0, border = border, flag = flag )

		hs.AddSpacer( 8 )
		
		self.upCategoryButton = wx.Button(self, label=_('Move &Up'), style=wx.BU_EXACTFIT)
		self.Bind( wx.EVT_BUTTON, self.onUpCategory, self.upCategoryButton )
		hs.Add( self.upCategoryButton, 0, border = border, flag = flag )

		self.downCategoryButton = wx.Button(self, label=_('Move D&own'), style=wx.BU_EXACTFIT)
		self.Bind( wx.EVT_BUTTON, self.onDownCategory, self.downCategoryButton )
		hs.Add( self.downCategoryButton, 0, border = border, flag = (flag & ~wx.LEFT) )

		hs.AddSpacer( 8 )
		
		self.addExceptionsButton = wx.Button(self, label=_('&Add Bib Exceptions'), style=wx.BU_EXACTFIT)
		self.Bind( wx.EVT_BUTTON, self.onAddExceptions, self.addExceptionsButton )
		hs.Add( self.addExceptionsButton, 0, border = border, flag = (flag & ~wx.LEFT) )

		hs.AddSpacer( 8 )
		
		self.updateStartWaveNumbersButton = wx.Button(self, label=_('&Update Start Wave Numbers'), style=wx.BU_EXACTFIT)
		self.Bind( wx.EVT_BUTTON, self.onUpdateStartWaveNumbers, self.updateStartWaveNumbersButton )
		hs.Add( self.updateStartWaveNumbersButton, 0, border = border, flag = (flag & ~wx.LEFT) )

		self.normalizeButton = wx.Button(self, label=_('N&ormalize'), style=wx.BU_EXACTFIT)
		self.Bind( wx.EVT_BUTTON, self.onNormalize, self.normalizeButton )
		hs.Add( self.normalizeButton, 0, border = border, flag = (flag & ~wx.LEFT) )

		hs.AddStretchSpacer()
		
		self.printButton = wx.Button( self, label=u'{}...'.format(_('Print')), style=wx.BU_EXACTFIT )
		self.Bind( wx.EVT_BUTTON, self.onPrint, self.printButton )
		hs.Add( self.printButton, 0, border = border, flag = (flag & ~wx.LEFT) )
		
		self.grid = ReorderableGrid( self )
		self.colNameFields = [
			(u'',						None),
			(_('Category Type'),		'catType'),
			(_('Active'),				'active'),
			(_('Name'),					'name'),
			(_('Gender'),				'gender'),
			(_('Numbers'),				'catStr'),
			(_('Start\nOffset'),		'startOffset'),
			(_('Race\nLaps'),			'numLaps'),
			(_('Lapped\nRiders\nContinue'),	'lappedRidersMustContinue'),
			(_('Distance'),				'distance'),
			(_('Dist.\nBy'),			'distanceType'),
			(_('First\nLap\nDist.'),	'firstLapDistance'),
			(_('80%\nLap\nTime'),		'rule80Time'),
			(_('CrossMgr\nEstimated\nLaps'),	'suggestedLaps'),
			(_('Upload'),				'uploadFlag'),
			(_('Series'),				'seriesFlag'),
		]
		self.computedFields = {'rule80Time', 'suggestedLaps'}
		self.colnames = [colName for colName, fieldName in self.colNameFields]
		self.iCol = dict( (fieldName, i) for i, (colName, fieldName) in enumerate(self.colNameFields) if fieldName )
		
		self.activeColumn = self.iCol['active']
		self.genderColumn = self.iCol['gender']
		self.numbersColumn = self.iCol['catStr']
		self.grid.CreateGrid( 0, len(self.colnames) )
		self.grid.SetRowLabelSize(32)
		self.grid.SetMargins(0,0)
		for col, name in enumerate(self.colnames):
			self.grid.SetColLabelValue( col, name )
			
		self.cb = None
		
		self.boolCols = set()
		self.choiceCols = set()
		self.readOnlyCols = set()
		self.dependentCols = set()
		
		# Set column attributes for the table.
		for col, (colName, fieldName) in enumerate(self.colNameFields):
			attr = gridlib.GridCellAttr()
			
			if fieldName is None:
				attr.SetRenderer( CategoryIconRenderer() )
				attr.SetAlignment( wx.ALIGN_LEFT, wx.ALIGN_CENTRE )
				attr.SetReadOnly( True )
				self.readOnlyCols.add( col )
				
			elif fieldName == 'catType':
				self.catTypeWidth = 64
				attr.SetEditor( gridlib.GridCellChoiceEditor(self.CategoryTypeChoices, False) )
				attr.SetAlignment( wx.ALIGN_LEFT, wx.ALIGN_CENTRE )
				self.choiceCols.add( col )
				
			elif fieldName in {'active', 'lappedRidersMustContinue', 'uploadFlag', 'seriesFlag'}:
				boolEditor = gridlib.GridCellBoolEditor()
				boolEditor.UseStringValues( '1', '0' )
				attr.SetEditor( boolEditor )
				attr.SetRenderer( gridlib.GridCellBoolRenderer() )
				attr.SetAlignment( wx.ALIGN_CENTRE, wx.ALIGN_CENTRE )
				self.boolCols.add( col )
				if fieldName == 'lappedRidersMustContinue':
					self.dependentCols.add( col )
				
			elif fieldName == 'gender':
				attr.SetEditor( gridlib.GridCellChoiceEditor([_('Open'),_('Men'),_('Women')], False) )
				self.choiceCols.add( col )
				
			elif fieldName == 'startOffset':
				attr.SetEditor( TimeEditor() )
				attr.SetAlignment( wx.ALIGN_CENTRE, wx.ALIGN_CENTRE )
				self.dependentCols.add( col )
				
			elif fieldName == 'numLaps':
				attr.SetEditor( wx.grid.GridCellNumberEditor() )
				attr.SetAlignment( wx.ALIGN_CENTRE, wx.ALIGN_CENTRE )
				self.dependentCols.add( col )
				
			elif fieldName in ['rule80Time', 'suggestedLaps']:
				attr.SetReadOnly( True )
				attr.SetAlignment( wx.ALIGN_CENTRE, wx.ALIGN_CENTRE )
				self.readOnlyCols.add( col )
				self.dependentCols.add( col )
				
			elif fieldName in ['distance', 'firstLapDistance'] :
				attr.SetEditor( gridlib.GridCellFloatEditor(7, 3) )
				attr.SetRenderer( gridlib.GridCellFloatRenderer(7, 3) )
				attr.SetAlignment( wx.ALIGN_CENTRE, wx.ALIGN_CENTRE )
				self.dependentCols.add( col )
				
			elif fieldName == 'distanceType':
				attr.SetEditor( gridlib.GridCellChoiceEditor(self.DistanceTypeChoices, False) )
				attr.SetAlignment( wx.ALIGN_RIGHT, wx.ALIGN_CENTRE )
				self.choiceCols.add( col )
				self.dependentCols.add( col )
				
			self.grid.SetColAttr( col, attr )
		
		self.Bind( gridlib.EVT_GRID_CELL_LEFT_CLICK, self.onGridLeftClick )
		self.Bind( gridlib.EVT_GRID_SELECT_CELL, self.onCellSelected )
		self.Bind( gridlib.EVT_GRID_CELL_CHANGE, self.onCellChanged )
		self.Bind( gridlib.EVT_GRID_EDITOR_CREATED, self.onEditorCreated )
		
		vs.Add( hs, 0, flag=wx.EXPAND|wx.ALL, border = 4 )
		vs.Add( self.grid, 1, flag=wx.GROW|wx.ALL|wx.EXPAND )
		
		self.rowCur = 0
		self.colCur = 0
		self.SetSizer(vs)

	def onPrint( self, event ):
		self.commit()
		PrintCategories()
	
	def onNormalize( self, event ):
		self.commit()
		if Model.race:
			Model.race.normalizeCategories()
			self.refresh()
			
	#------------------------------------------
	
	def onGridLeftClick( self, event ):
		if event.GetCol() in self.boolCols:
			r, c = event.GetRow(), event.GetCol()
			if c == self.iCol['active']:
				active = (self.grid.GetCellValue(r, self.iCol['active']) == u'1')
				wx.CallAfter( self.fixRow, r, self.CategoryTypeChoices.index(self.grid.GetCellValue(r, self.iCol['catType'])), not active )
			self.grid.SetCellValue( r, c, '1' if self.grid.GetCellValue(r, c) != '1' else '0' )
		event.Skip()
	
	def onCellSelected( self, event ):
		self.rowCur = event.GetRow()
		self.colCur = event.GetCol()
		if self.colCur in self.choiceCols or self.colCur in self.boolCols:
			wx.CallAfter( self.grid.EnableCellEditControl )
		event.Skip()

	def onCellChanged( self, event ):
		self.rowCur = event.GetRow()
		self.colCur = event.GetCol()
		if self.colCur in [1, 2]:
			self.fixCells()
		event.Skip()

	def onEditorCreated( self, event ):
		if event.GetCol() == self.numbersColumn:
			event.GetControl().Bind( wx.EVT_KEY_DOWN, self.onNumbersKeyEvent )
		event.Skip()
		
	def onNumbersKeyEvent( self, event ):
		if event.GetModifiers() == wx.MOD_CONTROL and event.GetKeyCode() == 86:
			if wx.TheClipboard.Open():
				data = wx.TextDataObject()
				if wx.TheClipboard.GetData(data):
					txt = data.GetText()
					txt = re.sub( '[^0-9,-]+', ',', txt )
					event.GetEventObject().WriteText( txt )
				wx.TheClipboard.Close()
				return
		
		event.Skip()

	#------------------------------------------

	def onUpdateStartWaveNumbers( self, event ):
		self.commit()
		undo.pushState()
		with Model.LockRace() as race:
			race.adjustAllCategoryWaveNumbers()
		wx.CallAfter( self.refresh )
		wx.CallAfter( Utils.refreshForecastHistory )

	def onAddExceptions( self, event ):
		with Model.LockRace() as race:
			if not race or not race.getAllCategories():
				return
				
		r = self.grid.GetGridCursorRow()
		if r is None or r < 0:
			Utils.MessageOK( self, _('You must select a Category first'), _('Select a Category') )
			return
		
		with Model.LockRace() as race:
			categories = race.getAllCategories()
			category = categories[r]
			
		dlg = wx.TextEntryDialog(
			self,
			u'{}: {}'.format(
				category.name,
				_('''Add Bib Exceptions (comma separated).
This will add the given list of Bibs to this category,
and remove them from other categories.'''),
			),
			_('Add Bib Exceptions')
		)
		good = (dlg.ShowModal() == wx.ID_OK)
		if good:
			response = dlg.GetValue()
		dlg.Destroy()
		if not good:
			return

		undo.pushState()
		response = re.sub( '[^0-9,]', '', response.replace(' ', ',') )
		with Model.LockRace() as race:
			for numException in response.split(','):
				race.addCategoryException( category, numException )

		self.refresh()
		
	def _setRow( self, r, active, name, catStr, startOffset = '00:00:00',
					numLaps = None,
					lappedRidersMustContinue = False,
					distance = None, distanceType = None,
					firstLapDistance = None, gender = None,
					catType = Model.Category.CatWave,
					uploadFlag = True, seriesFlag = True ):
					
		if len(startOffset) < len('00:00:00'):
			startOffset = '00:' + startOffset
			
		GetTranslation = _
		gender = gender if gender in ['Men', 'Women'] else 'Open'
		self.grid.SetRowLabelValue( r, u'' )
		self.grid.SetCellValue( r, self.iCol['active'], u'1' if active else u'0' )
		self.grid.SetCellValue( r, self.iCol['catType'], self.CategoryTypeChoices[catType] )
		self.grid.SetCellValue( r, self.iCol['name'], name )
		self.grid.SetCellValue( r, self.iCol['gender'], GetTranslation(gender) )
		self.grid.SetCellValue( r, self.iCol['catStr'], catStr )
		self.grid.SetCellValue( r, self.iCol['startOffset'], startOffset )
		self.grid.SetCellValue( r, self.iCol['numLaps'], u'{}'.format(numLaps) if numLaps else '' )
		self.grid.SetCellValue( r, self.iCol['lappedRidersMustContinue'], u'1' if lappedRidersMustContinue else u'0' )
		self.grid.SetCellValue( r, self.iCol['rule80Time'], '' )
		self.grid.SetCellValue( r, self.iCol['suggestedLaps'], '' )
		self.grid.SetCellValue( r, self.iCol['distance'], ('%.3f' % distance) if distance else '' )
		self.grid.SetCellValue( r, self.iCol['distanceType'], self.DistanceTypeChoices[distanceType if distanceType else 0] )
		self.grid.SetCellValue( r, self.iCol['firstLapDistance'], ('%.3f' % firstLapDistance) if firstLapDistance else '' )
		self.grid.SetCellValue( r, self.iCol['uploadFlag'], u'1' if uploadFlag else u'0' )
		self.grid.SetCellValue( r, self.iCol['seriesFlag'], u'1' if seriesFlag else u'0' )
		
		race = Model.race
		category = race.categories.get(u'{} ({})'.format(name.strip(), gender), None)
		if not category or category.catType != Model.Category.CatWave:
			return
			
		# Get the 80% time cutoff.
		if not active or not Model.race:
			return
			
		rule80Time = race.getRule80CountdownTime( category )
		if rule80Time:
			self.grid.SetCellValue( r, self.iCol['rule80Time'], Utils.formatTime(rule80Time) )
		
		laps = race.getCategoryRaceLaps().get(category, 0)
		if laps:
			self.grid.SetCellValue( r, self.iCol['suggestedLaps'], '{}'.format(laps) )
	
	def fixRow( self, row, catType, active ):
		activeColour = wx.WHITE if active else self.inactiveColour
		colour = activeColour if catType == Model.Category.CatWave else self.ignoreColour
		for colName, fieldName in self.colNameFields:
			if not fieldName:
				continue
			col = self.iCol[fieldName]
			if col in self.dependentCols:
				self.grid.SetCellBackgroundColour( row, col, colour )
			else:
				self.grid.SetCellBackgroundColour( row, col, activeColour )
		
	def fixCells( self, event = None ):
		for row in xrange(self.grid.GetNumberRows()):
			active = self.grid.GetCellValue( row, self.iCol['active'] )[:1] in 'TtYy1'
			catType = self.CategoryTypeChoices.index(self.grid.GetCellValue(row, self.iCol['catType']) )
			self.fixRow( row, catType, active )
	
	def onActivateAll( self, event ):
		for c in Model.race.getAllCategories():
			if not c.active:
				c.active = True
				Model.race.setChanged()
		wx.CallAfter( self.refresh )
		
	def onDeactivateAll( self, event ):
		for c in Model.race.getAllCategories():
			if c.active:
				c.active = False
				Model.race.setChanged()
		wx.CallAfter( self.refresh )
		
	def onNewCategory( self, event ):
		self.grid.AppendRows( 1 )
		self._setRow( r=self.grid.GetNumberRows() - 1, active=True, name=u'<{}>     '.format(_('CategoryName')), catStr='100-199,504,-128' )
		self.grid.AutoSizeColumns( False )
		
	def onDelCategory( self, event ):
		r = self.grid.GetGridCursorRow()
		if r is None or r < 0:
			return
		if Utils.MessageOKCancel(
					self,
					u'{} "{} ({})"?'.format(
						_('Delete Category'),
						self.grid.GetCellValue(r, 3).strip(),
						self.grid.GetCellValue(r, 4).strip(),
					),
					_('Delete Category') ):
			self.grid.DeleteRows( r, 1, True )
		
	def onUpCategory( self, event ):
		self.grid.SaveEditControlValue()
		self.grid.DisableCellEditControl()
		r = self.grid.GetGridCursorRow()
		Utils.SwapGridRows( self.grid, r, r-1 )
		if r-1 >= 0:
			self.grid.MoveCursorUp( False )
		self.grid.ClearSelection()
		self.grid.SelectRow( max(r-1, 0), True )
		
	def onDownCategory( self, event ):
		self.grid.SaveEditControlValue()
		self.grid.DisableCellEditControl()
		r = self.grid.GetGridCursorRow()
		Utils.SwapGridRows( self.grid, r, r+1 )
		if r+1 < self.grid.GetNumberRows():
			self.grid.MoveCursorDown( False )
		self.grid.ClearSelection()
		self.grid.SelectRow( min(r+1, self.grid.GetNumberRows()-1), True )
		
	def refresh( self ):
		# Fix the height of the column labels.
		dc = wx.WindowDC( self.grid )
		dc.SetFont( self.grid.GetLabelFont() )
		textHeight = dc.GetTextExtent( 'Label' )[1]
		self.colLabelHeight = textHeight * max(name.count('\n') + 1 for name in self.colnames) + textHeight // 4
		self.grid.SetColLabelSize( self.colLabelHeight )
			
		with Model.LockRace() as race:
			self.grid.ClearGrid()
			if race is None:
				return
			
			for c in xrange(self.grid.GetNumberCols()):
				if self.grid.GetColLabelValue(c).startswith(_('Distance')):
					self.grid.SetColLabelValue( c, u'{}\n({})'.format(_('Distance'), ['km', 'miles'][getattr(race, 'distanceUnit', 0)]) )
					break
			
			categories = race.getAllCategories()
			
			if self.grid.GetNumberRows() > 0:
				self.grid.DeleteRows( 0, self.grid.GetNumberRows() )
			self.grid.AppendRows( len(categories) )

			for r, cat in enumerate(categories):
				self._setRow(	r=r,
								active				= cat.active,
								name				= cat.name,
								gender				= getattr(cat, 'gender', None),
								catStr				= cat.catStr,
								catType				= cat.catType,
								startOffset			= cat.startOffset,
								numLaps				= cat.numLaps,
								lappedRidersMustContinue = getattr(cat, 'lappedRidersMustContinue', False),
								distance			= getattr(cat, 'distance', None),
								distanceType		= getattr(cat, 'distanceType', Model.Category.DistanceByLap),
								firstLapDistance	= getattr(cat, 'firstLapDistance', None),
								uploadFlag			= cat.uploadFlag,
								seriesFlag			= cat.seriesFlag,
							)
				
			self.grid.AutoSizeColumns( False )
			self.fixCells()
			
			# Force the grid to the correct size.
			self.grid.FitInside()
			self.GetSizer().Layout()

	def commit( self ):
		undo.pushState()
		with Model.LockRace() as race:
			self.grid.SaveEditControlValue()
			self.grid.DisableCellEditControl()	# Make sure the current edit is committed.
			if race is None:
				return
			numStrTuples = []
			for r in xrange(self.grid.GetNumberRows()):
				values = dict( (name, self.grid.GetCellValue(r, c)) for name, c in self.iCol.iteritems()
																			if name not in self.computedFields )
				values['catType'] = self.CategoryTypeChoices.index(values['catType'])
				values['distanceType'] = self.DistanceTypeChoices.index(values['distanceType'])
				numStrTuples.append( values )
			race.setCategories( numStrTuples )
			race.adjustAllCategoryWaveNumbers()
		wx.CallAfter( Utils.refreshForecastHistory )
	
if __name__ == '__main__':
	app = wx.App(False)
	mainWin = wx.Frame(None,title="CrossMan", size=(1000,400))
	Model.setRace( Model.Race() )
	race = Model.getRace()
	race._populate()
	race.setCategories( [
							{'name':'test1', 'catStr':'100-199,999','gender':'Men'},
							{'name':'test2', 'catStr':'200-299,888', 'startOffset':'00:10', 'distance':'6'},
							{'name':'test3', 'catStr':'300-399', 'startOffset':'00:20','gender':'Women'},
							{'name':'test4', 'catStr':'400-499', 'startOffset':'00:30','gender':'Open'},
							{'name':'test5', 'catStr':'500-599', 'startOffset':'01:00','gender':'Men'},
						] )
	categories = Categories(mainWin)
	categories.refresh()
	mainWin.Show()
	app.MainLoop()
