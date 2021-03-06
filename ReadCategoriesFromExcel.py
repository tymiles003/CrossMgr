import Utils
import Model

sheetName = '--CrossMgr-Categories'

def ReadCategoriesFromExcel( reader ):
	race = Model.race
	if not race:
		return False
		
	HeadersFields = (
		('Category Type',	'catType'),
		('Name',			'name'),
		('Gender',			'gender'),
		('Numbers',			'catStr'),
		('Start Offset',	'startOffset'),
		('Race Laps',		'numLaps'),
		('Race Distance',	'distance'),
		('Race Minutes',	None),
	)

	HeadersToFields = dict( (k, v) for k, v in HeadersFields )
	HeaderSet = set( k for k, v in HeadersFields )

	if sheetName not in reader.sheet_names():
		return False
	
	headerMap = {}
	categories = []
	for r, row in enumerate(reader.iter_list(sheetName)):
		# Since this is machine generated, assume the headers are in the first row.
		if not headerMap:
			for c, v in enumerate(row):
				if v in HeaderSet:
					headerMap[v] = c
			continue
		
		catRow = {}
		for h, c in headerMap.iteritems():
			catField = HeadersToFields[h]
			if catField is None:
				continue
			catRow[catField] = row[c]
			
		categories.append( catRow )
	
	if categories:
		try:
			race.setCategories( race.mergeExistingCategoryAttributes(categories) )
			race.adjustAllCategoryWaveNumbers()
			return True
		except Exception as e:
			Utils.writeLog( 'ReadCategoriesFromExcel: error: {}'.format(e) )
			return False
	else:
		return False
