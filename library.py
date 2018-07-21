"""
# Factors library providing high level access to the structuring and formatting routines
# used to construct a Product Snapshot.
"""
import typing
import itertools

from ..system import files
from ..system import python

from ..filesystem import library as libfs
from ..text import library as libtext
from ..system import libfactor
from ..xml import libfactor as xmlfactor
from ..xml import library as libxml

from . import libhtml

namespaces = {
	'xlink': 'http://www.w3.org/1999/xlink',
	'inspect': 'http://fault.io/xml/inspect#set',
}

def extract_inspect(xml, href='{%s}href' %(namespaces['xlink'],)):
	"""
	# Load the inspect processed factor.

	# [Parameters]
	# /xml/
		# The XML document containing the constructed inspect output.

	# [Returns]

	# /&tuple
		# /(&object)`0`/
			# Command Parameters.
		# /(&set)`1`/
			# The set of sources.
	"""

	e = xml.getroot()

	# Stored parameters of the link. (library.set)
	params = e.find("./inspect:parameters", namespaces)
	if params is not None:
		data, = params
		s = libxml.Data.structure(data)
	else:
		s = None

	# Source file.
	sources = e.findall("./inspect:source", namespaces)
	sources = [files.Path.from_absolute(x.attrib[href].replace('file://', '', 1)) for x in sources]

	return s, sources

def construct_corpus_map(directory, index):
	content = libxml.element('map',
		itertools.chain.from_iterable(
			libxml.element('item',
				libxml.escape_element_string(str(r)),
				('key', k)
			)
			for k, r in index.items()
		),
		('dictionary', directory),
		('xmlns', 'http://fault.io/xml/filesystem#index'),
	)

	return b''.join(content)

def factors(package:str) -> typing.Tuple[
		python.Import,
		typing.Sequence[python.Import],
		typing.Sequence[python.Import]
	]:
	"""
	# Construct and return the factors (modules and packages) contained within
	# the given &package string.

	# [ Returns ]
	# `(root, (packages, modules))`; where root is the &package parameter
	# as an &python.Import.

	# All objects are &..routes.library.Import instances pointing to the module.

	# [ Parameters ]

	# /package/
		# The path to the package.
	"""

	root = python.Import.from_fullname(package)
	return (root, root.tree())

def fractions(packages:python.Import) -> typing.Mapping[
		python.Import,
		typing.Sequence[python.Import],
	]:
	"""
	# Construct a mapping detailing the factors that consist of a set of fractions.
	# Factors that represent the construction of a set of fractions are used to manage
	# build targets.

	# [ Returns ]
	# The constructed mapping. The keys are the &python.Import instances,
	# and the values are sequences.

	# [ Parameters ]
	# /packages/
		# The set of factor packages to inspect in order to find the associated fractions.
	"""

	return {
		x: libfactor.sources(x)
		for x in packages
		if libfactor.composite(x)
	}

from . import libhtml
html = xmlfactor.Library.open(libhtml)

def transform(path, **params):
	input = xmlfactor.readfile(path)
	return html.xslt('factor', **params)(input)

def index(name, roots, **params):
	"""
	# Create the product index for the set of root factors.
	"""

	rstr = ','.join(roots)
	params['roots'] = rstr
	subs = ''.join("<subfactor identifier='%s'/>" %(x,) for x in roots)
	ctx = "<context name='%s' type='product' path='' icon='🏛'/>" % (name,)
	xmlstr = "<factor type='product' xmlns='http://fault.io/xml/fragments'>%s%s</factor>"
	input = xmlfactor.readstring((xmlstr %(ctx, subs)).encode('utf-8'))

	return html.xslt('corpus', **params)(input)
