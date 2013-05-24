import os
import wx
import wx.grid			as gridlib
from wx.lib import masked
import math
import Model
import Utils
from ReorderableGrid import ReorderableGrid
from HighPrecisionTimeEdit import HighPrecisionTimeEdit
from PhotoFinish import TakePhoto, AddBibToPhoto
import OutputStreamer

def formatTime( secs ):
	if secs is None:
		secs = 0
	if secs < 0:
		sign = '-'
		secs = -secs
	else:
		sign = ''
	f, ss = math.modf(secs)
	secs = int(ss)
	hours = int(secs // (60*60))
	minutes = int( (secs // 60) % 60 )
	secs = secs % 60
	decimal = '.%03d' % int( f * 1000 )
	return " %s%02d:%02d:%02d%s " % (sign, hours, minutes, secs, decimal)

class HighPrecisionTimeEditor(gridlib.PyGridCellEditor):
	Empty = '00:00:00.000'
	def __init__(self):
		self._tc = None
		self.startValue = self.Empty
		gridlib.PyGridCellEditor.__init__(self)
		
	def Create( self, parent, id, evtHandler ):
		self._tc = HighPrecisionTimeEdit(parent, id, allow_none = False, style = wx.TE_PROCESS_ENTER)
		self.SetControl( self._tc )
		if evtHandler:
			self._tc.PushEventHandler( evtHandler )
	
	def SetSize( self, rect ):
		self._tc.SetDimensions(rect.x, rect.y, rect.width+2, rect.height+2, wx.SIZE_ALLOW_MINUS_ONE )
	
	def BeginEdit( self, row, col, grid ):
		self.startValue = grid.GetTable().GetValue(row, col).strip()
		self._tc.SetValue( self.startValue )
		self._tc.SetFocus()
		
	def EndEdit( self, row, col, grid ):
		changed = False
		val = self._tc.GetValue()
		if val != self.startValue:
			if val == self.Empty:
				val = ''
			change = True
			grid.GetTable().SetValue( row, col, val )
		self.startValue = self.Empty
		self._tc.SetValue( self.startValue )
		
	def Reset( self ):
		self._tc.SetValue( self.startValue )
		
	def Clone( self ):
		return HighPrecisionTimeEditor()

class BibEditor(gridlib.PyGridCellEditor):
	def __init__(self):
		self._tc = None
		self.startValue = ''
		gridlib.PyGridCellEditor.__init__(self)
		
	def Create( self, parent, id, evtHandler ):
		self._tc = masked.NumCtrl( parent, id, style = wx.TE_PROCESS_ENTER )
		self._tc.SetAllowNone( True )
		self.SetControl( self._tc )
		if evtHandler:
			self._tc.PushEventHandler( evtHandler )
	
	def SetSize( self, rect ):
		self._tc.SetDimensions(rect.x, rect.y, rect.width+2, rect.height+2, wx.SIZE_ALLOW_MINUS_ONE )
	
	def BeginEdit( self, row, col, grid ):
		self.startValue = int(grid.GetTable().GetValue(row, col).strip() or 0)
		self._tc.SetValue( self.startValue )
		self._tc.SetFocus()
		
	def EndEdit( self, row, col, grid ):
		changed = False
		val = self._tc.GetValue()
		val = str(val) if val else ''
		if val != str(self.startValue):
			change = True
			grid.GetTable().SetValue( row, col, val )
		self._tc.SetValue( self.startValue )
		
	def Reset( self ):
		self._tc.SetValue( self.startValue )
		
	def Clone( self ):
		return BibEditor()
		
class TimeTrialRecord( wx.Panel ):
	def __init__( self, parent, controller, id = wx.ID_ANY ):
		wx.Panel.__init__(self, parent, id)
		self.controller = controller

		self.headerNames = ['Time', 'Bib']
		
		self.maxRows = 12
		
		fontSize = 18
		self.font = wx.FontFromPixelSize( wx.Size(0,fontSize), wx.FONTFAMILY_SWISS, wx.NORMAL, wx.FONTWEIGHT_NORMAL )
		self.bigFont = wx.FontFromPixelSize( wx.Size(0,int(fontSize*1.3)), wx.FONTFAMILY_SWISS, wx.NORMAL, wx.FONTWEIGHT_NORMAL )
		self.vbs = wx.BoxSizer(wx.VERTICAL)
		
		self.recordTimeButton = wx.Button( self, wx.ID_ANY, 'New Time' )
		self.recordTimeButton.Bind( wx.EVT_BUTTON, self.doRecordTime )
		self.recordTimeButton.SetFont( self.bigFont )
		
		bitmap = wx.Bitmap( os.path.join(Utils.getImageFolder(), 'camera.png'), wx.BITMAP_TYPE_PNG )
		self.photoButton = wx.BitmapButton( self, wx.ID_ANY, bitmap )
		self.photoButton.Bind( wx.EVT_BUTTON, self.doPhoto )
		
		hbs = wx.BoxSizer( wx.HORIZONTAL )
		hbs.Add( self.recordTimeButton, 0 )
		hbs.AddStretchSpacer()
		hbs.Add( self.photoButton, 0 )
		
		self.grid = ReorderableGrid( self, style = wx.BORDER_SUNKEN )
		self.grid.SetFont( self.font )
		self.grid.EnableReorderRows( False )
		self.grid.SetRowLabelSize( 0 )
		self.grid.CreateGrid( self.maxRows, len(self.headerNames) )
		for col, name in enumerate(self.headerNames):
			self.grid.SetColLabelValue( col, name )
		self.grid.SetLabelFont( self.font )
		for col in xrange(self.grid.GetNumberCols()):
			attr = gridlib.GridCellAttr()
			attr.SetFont( self.font )
			if col == 0:
				attr.SetEditor( HighPrecisionTimeEditor() )
			elif col == 1:
				attr.SetRenderer( gridlib.GridCellNumberRenderer() )
				attr.SetEditor( BibEditor() )
			self.grid.SetColAttr( col, attr )
		
		self.commitButton = wx.Button( self, wx.ID_ANY, 'Commit' )
		self.commitButton.Bind( wx.EVT_BUTTON, self.doCommit )
		self.commitButton.SetFont( self.bigFont )
		
		self.vbs.Add( hbs, 0, flag=wx.ALL|wx.EXPAND, border = 4 )
		self.vbs.Add( self.grid, 1, flag=wx.ALL|wx.EXPAND, border = 4 )
		self.vbs.Add( self.commitButton, flag=wx.ALL|wx.ALIGN_RIGHT, border = 4 )
		
		self.Bind(wx.EVT_MENU, self.doRecordTime, id=self.recordTimeButton.GetId())
		self.Bind(wx.EVT_MENU, self.doCommit, id=self.commitButton.GetId())
		self.Bind(wx.EVT_MENU, self.doPhoto, id=self.photoButton.GetId())
		accel_tbl = wx.AcceleratorTable([
			(wx.ACCEL_NORMAL,  ord('T'), self.recordTimeButton.GetId() ),
			(wx.ACCEL_NORMAL,  ord('C'), self.commitButton.GetId() ),
			(wx.ACCEL_NORMAL,  ord('P'), self.photoButton.GetId() ),
		])
		self.SetAcceleratorTable(accel_tbl)
		
		
		self.SetSizer(self.vbs)
		
	def doPhoto( self, event ):
		if not Utils.mainWin or not getattr(Model.race, 'enableUSBCamera', False):
			return
			
		row = self.grid.GetGridCursorRow()
		tStr = self.grid.GetCellValue( row, 0 )
		if not tStr:
			return
			
		Utils.mainWin.photoDialog.Show( True )
		Utils.mainWin.photoDialog.refresh( 0, Utils.StrToSeconds(tStr) )
	
	def doRecordTime( self, event ):
		t = Model.race.curRaceTime()
		
		# Trigger the camera.
		with Model.LockRace() as race:
			if not race:
				return
			if getattr(race, 'enableUSBCamera', False):
				race.photoCount = getattr(race,'photoCount',0) + TakePhoto( Utils.getFileName(), 0, Utils.StrToSeconds(formatTime(t)) )
	
		# Find the last row without a time.
		self.grid.SetGridCursor( 0, 0, )
		
		emptyRow = self.grid.GetNumberRows() + 1
		success = False
		for i in xrange(2):
			for row in xrange(self.grid.GetNumberRows()):
				if not self.grid.GetCellValue(row, 0):
					emptyRow = row
					break
			if emptyRow >= self.grid.GetNumberRows():
				self.doCommit( event )
			else:
				success = True
				break
		
		if not success:
			Utils.MessageOK( self, 'Insufficient space to Record Time.\nEnter Bib numbers and press Commit.\nOr delete some entries', 'Record Time Failed.' )
			return
			
		self.grid.SetCellValue( emptyRow, 0, formatTime(t) )
		
		# Set the edit cursor at the first empty bib position.
		for row in xrange(self.grid.GetNumberRows()):
			text = self.grid.GetCellValue(row, 1)
			if not text or text == '0':
				self.grid.SetGridCursor( row, 1 )
				break
		
	def doCommit( self, event ):
		self.grid.SetGridCursor( 0, 0, )
	
		# Find the last row without a time.
		timesBibs = []
		timesNoBibs = []
		for row in xrange(self.grid.GetNumberRows()):
			tStr = self.grid.GetCellValue(row, 0).strip()
			bib = self.grid.GetCellValue(row, 1).strip()
			if not tStr:
				continue
			if bib:
				try:
					bib = int(bib)
				except:
					continue
				timesBibs.append( (tStr, bib) )
			else:
				timesNoBibs.append( tStr )
				
		for row in xrange(self.grid.GetNumberRows()):
			for column in xrange(self.grid.GetNumberCols()):
				self.grid.SetCellValue(row, column, '' )
		
		'''
		for row, tStr in enumerate(timesNoBibs):
			self.grid.SetCellValue( row, 0, tStr )
		'''
			
		self.grid.SetGridCursor( 0, 1 )
			
		if timesBibs and Model.race:
			with Model.LockRace() as race:
				isCamera = getattr(race, 'enableUSBCamera', False)
				for tStr, bib in timesBibs:
					raceSeconds = Utils.StrToSeconds(tStr)
					race.addTime( bib, raceSeconds )
					if isCamera:
						AddBibToPhoto( bib, raceSeconds )
					OutputStreamer.writeNumTime( bib, t )
						
			wx.CallAfter( Utils.refresh )
			
		self.grid.SetGridCursor( 0, 1 )
	
	def refresh( self ):
		self.grid.AutoSizeRows( False )
		
		dc = wx.WindowDC( self.grid )
		dc.SetFont( self.font )
		
		width, height = dc.GetTextExtent(" 00:00:00.000 ")
		self.grid.SetColSize( 0, width )
		
		width, height = dc.GetTextExtent(" 9999 ")
		self.grid.SetColSize( 1, width )
		
		self.grid.ForceRefresh()
		
	def commit( self ):
		pass
		
if __name__ == '__main__':
	Utils.disable_stdout_buffering()
	app = wx.PySimpleApp()
	mainWin = wx.Frame(None,title="CrossMan", size=(600,600))
	Model.setRace( Model.Race() )
	Model.getRace()._populate()
	timeTrialRecord = TimeTrialRecord(mainWin, None)
	timeTrialRecord.refresh()
	mainWin.Show()
	app.MainLoop()