#!/usr/bin/env python

import os
import json
import re
import urllib
import cStringIO
from utils.UnicodeIO import UnicodeReader, UnicodeWriter
from db.Corpus_DB import Corpus_DB

class Home_Core(object):
	def __init__(self, request, response):
		self.request = request
		self.response = response
		self.params = {}
		self.content = {}   # All variables returned by an API call
		self.table = []     # Primary variable returned by an API call as rows of records
		self.header = []    # Header for primary variable
		self.configs = self.GetConfigs()
		self.menus = self.GetMenus()

################################################################################
# Server, Dataset, Model, and Attribute

	def GetConfigs(self):
		server = self.GetServer()
		dataset = self.GetDataset(server)
		model = self.GetModel(server, dataset)
		attribute = self.GetAttribute(server, dataset, model)
		url = self.GetURL()
		configs = {
			'server' : server,
			'dataset' : dataset,
			'model' : model,
			'attribute' : attribute,
			'url' : url,
			'is_text' : self.IsTextFormat(),
			'is_graph' : self.IsGraphFormat(),
			'is_json' : self.IsJsonFormat(),
			'is_csv' : self.IsCSVFormat(),
			'is_tsv' : self.IsTSVFormat()
		}
		return configs

	def GetServer(self):
		return self.request.env['HTTP_HOST']

	def GetDataset(self, server):
		return self.request.application

	def GetModel(self, server, dataset):
		return self.request.controller

	def GetAttribute(self, server, dataset, model):
		return self.request.function
	
	def GetURL(self):
		return self.request.env['wsgi_url_scheme'] + '://' + self.request.env['HTTP_HOST'] + self.request.env['PATH_INFO']
	
################################################################################
# Menus for datasets, models, attributes, etc.

	def GetMenus(self):
		server = self.configs['server']
		dataset = self.configs['dataset']
		model = self.configs['model']
		attribute = self.configs['attribute']

		operations = self.GetOperations(server)
		datasets = self.GetDatasets(server)
		views = self.GetViews(server)
		models = self.GetModels(server, dataset)
		attributes = self.GetAttributes(server, dataset, model, attribute)
		menus = {
			'server' : server,
			'dataset' : dataset,
			'model' : model,
			'attribute' : attribute,

			'datasets' : datasets,
			'operations' : operations,
			'models' : models,
			'views' : views,
			'attributes' : attributes
		}
		return menus

	def GetOperations(self, server):
		operations = [
			{ 'value' : 'dataset', 'name' : 'Upload a new dataset' }
		]
		self.configs.update({
			'AvailableOperations' : operations
		})
		return operations

	def GetViews(self, server):
		views = []
		self.configs.update({
			'AvailableVisualizations' : views
		})
		return views
		
	EXCLUDE_SYSTEM_FOLDERS = frozenset([ 'admin', 'examples', 'welcome', 'init', 'dataset' ])
	EXCLUDE_VIS_FOLDERS = frozenset([])
	EXCLUDE_TEMP_FOLDERS = re.compile(r'^temp_.*$')
	def IsExcludedDataset(self, folder):
		if folder in Home_Core.EXCLUDE_SYSTEM_FOLDERS:
			return True
		elif folder in Home_Core.EXCLUDE_VIS_FOLDERS:
			return True
		elif Home_Core.EXCLUDE_TEMP_FOLDERS.match(folder) is not None:
			return True
		else:
			return False

	def GetDatasets(self, server):
		folders = []
		applications_path = '{}/applications'.format(self.request.env['applications_parent'])
		for folder in os.listdir(applications_path):
			if not self.IsExcludedDataset(folder):
				applications_subpath = '{}/{}'.format(applications_path, folder)
				if os.path.isdir(applications_subpath):
					folders.append(folder)
		datasets = sorted(folders)
		if self.configs['dataset'] == 'init':
			self.content.update({
				'AvailableDatasets' : datasets
			})
		return datasets

	def GetModels(self, server, dataset):
		models = []
		if not self.IsExcludedDataset(dataset):
			with Corpus_DB() as corpus_db:
				rows = corpus_db.GetModels()
			models = [{
				'value' : row['model_key'],
				'name' : row['model_desc']
			} for row in rows ]
			if self.configs['model'] == 'default':
				self.content.update({
					'AvailableModels' : models
				})
		return models
	
	def GetAttributes(self, server, dataset, model, attribute):
		attributes = []
		if not self.IsExcludedDataset(dataset):
			if model != 'default':
				if model == 'lda':
					attributes = [
						'Vocab',
						'DocList',
						'TermList',
						'TopicList',
						'TermTopicMatrix',
						'DocTopicMatrix',
						'TopicCovariance',
						'TopTerms',
						'TopDocs'
					]
				if model == 'itm':
					attributes = [
						'Update',
						'gib'
					]
				if model == 'corpus':
					attributes = [
						'DocumentByIndex',
						'DocumentById',
						'SearchDocuments',
						'Metadata',
						'TermFreqs',
						'TermProbs',
						'TermCoFreqs',
						'TermCoProbs',
						'TermG2',
						'SentenceCoFreqs',
						'SentenceCoProbs',
						'SentenceG2'
					]
				if self.configs['attribute'] == 'index':
					self.content.update({
						'AvailableAttributes' : attributes
					})
		return attributes

################################################################################
# Parameters

	def GetStringParam( self, key ):
		if key in self.request.vars:
			return unicode(self.request.vars[key])
		else:
			return None
		
	def GetNonNegativeIntegerParam( self, key ):
		try:
			n = int(self.request.vars[key])
			if n >= 0:
				return n
			else:
				return 0
		except:
			return None

	def GetNonNegativeFloatParam( self, key ):
		try:
			n = float(self.request.vars[key])
			if n >= 0:
				return n
			else:
				return 0.0
		except:
			return None
	
################################################################################
# Generate a response

	def IsDebugMode( self ):
		return 'debug' in self.request.vars
	
	def IsTextFormat( self ):
		return not self.IsGraphFormat() and not self.IsJsonFormat()
	
	def IsGraphFormat( self ):
		return 'format' in self.request.vars and 'graph' == self.request.vars['format'].lower()

	def IsJsonFormat( self ):
		return 'format' in self.request.vars and 'json' == self.request.vars['format'].lower()

	def IsCSVFormat( self ):
		return 'format' in self.request.vars and 'csv' == self.request.vars['format'].lower()
	
	def IsTSVFormat( self ):
		return 'format' in self.request.vars and 'tsv' == self.request.vars['format'].lower()
	
	def IsMachineFormat( self ):
		return self.IsJsonFormat() or self.IsGraphFormat() or self.IsCSVFormat() or self.IsTSVFormat()
	
	def HasAllowedOrigin( self ):
		return 'origin' in self.request.vars
	
	def GetAllowedOrigin( self ):
		return self.request.vars['origin']
	
	def GenerateResponse( self ):
		if self.IsDebugMode():
			return self.GenerateDebugResponse()
		else:
			return self.GenerateNormalResponse()
	
	def GenerateDebugResponse( self ):
		envObject = self.request.env
		envJSON = {}
		for key in envObject:
			value = envObject[ key ]
			if isinstance( value, dict ) or \
			   isinstance( value, list ) or isinstance( value, tuple ) or \
			   isinstance( value, str ) or isinstance( value, unicode ) or \
			   isinstance( value, int ) or isinstance( value, long ) or isinstance( value, float ) or \
			   value is None or value is True or value is False:
				envJSON[ key ] = value
			else:
				envJSON[ key ] = 'Value not JSON-serializable'
		
		data = {
			'env' : envJSON,
			'cookies' : self.request.cookies,
			'vars' : self.request.vars,
			'get_vars' : self.request.get_vars,
			'post_vars' : self.request.post_vars,
			'folder' : self.request.folder,
			'application' : self.request.application,
			'controller' : self.request.controller,
			'function' : self.request.function,
			'args' : self.request.args,
			'extension' : self.request.extension,
			'now' : str( self.request.now ),
			'configs' : self.configs,
			'params' : self.params
		}
		data.update( self.content )
		dataStr = json.dumps( data, encoding = 'utf-8', indent = 2, sort_keys = True )
		
		self.response.headers['Content-Type'] = 'application/json'
		return dataStr

	def GenerateNormalResponse( self ):
		if self.IsJsonFormat():
			data = { 'configs' : self.configs }
			data.update(self.content)
			dataStr = json.dumps( self.content, encoding = 'utf-8', indent = 2, sort_keys = True )
			self.response.headers['Content-Type'] = 'application/json'
			if self.HasAllowedOrigin():
				self.response.headers['Access-Control-Allow-Origin'] = self.GetAllowedOrigin()
			return dataStr

		if self.IsCSVFormat():
			f = cStringIO.StringIO()
			writer = UnicodeWriter(f)
			writer.writerow( [ d['name'] for d in self.header ] )
			for record in self.table:
				row = [ record[d['name']] for d in self.header ]
				writer.writerow(row)
			dataStr = f.getvalue()
			f.close()
			self.response.headers['Content-Type'] = 'text/csv; charset=utf-8'
			if self.HasAllowedOrigin():
				self.response.headers['Access-Control-Allow-Origin'] = self.GetAllowedOrigin()
			return dataStr
		
		if self.IsTSVFormat():
			headerStr = u'\t'.join( d['name'] for d in self.header )
			rowStrs = []
			for record in self.table:
				rowStrs.append( u'\t'.join( u'{}'.format( record[d['name']]) for d in self.header ) )
			tableStr = u'\n'.join(rowStrs)
			dataStr = u'{}\n{}\n'.format( headerStr, tableStr ).encode('utf-8')
			self.response.headers['Content-Type'] = 'text/tab-separated-values; charset=utf-8'
			if self.HasAllowedOrigin():
				self.response.headers['Access-Control-Allow-Origin'] = self.GetAllowedOrigin()
			return dataStr
	
		data = {
			'configs' : self.configs,
			'menus' : self.menus,
			'params' : self.params
		}
		data.update( self.content )
		data['content'] = json.dumps( self.content, encoding = 'utf-8', indent = 2, sort_keys = True )
		self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
		return data
