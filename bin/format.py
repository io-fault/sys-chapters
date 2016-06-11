"""
Format the referenced structure set into a &..filesystem.library.Dictionary instance.
"""

import sys
import itertools
import os.path
import lzma
import types
import importlib.machinery
import io

from ...routes import library as libroutes
from ...xml import library as libxml
from ...filesystem import library as libfs

from .. import xslt

def index_xml(directory, index):
	content = libxml.element('map',
		itertools.chain.from_iterable(
			libxml.element('item',
				libxml.escape_element_string(str(r)),
				('key', k)
			)
			for k, r in index.items()
		),
		('dictionary', directory),
		('xmlns', 'https://fault.io/xml/filesystem#index'),
	)

	return b''.join(content)

def main(source, target, metrics=None, suffix='.html'):
	src = os.path.realpath(source)
	structs = libfs.Dictionary.open(src)
	formats = libfs.Dictionary.create(libfs.Hash(), os.path.realpath(target))

	index = {
		k.decode('utf-8'): r
		for k, r in structs.references()
	}
	xml = index_xml(src, index)

	# temporary for the index.xml file
	with libroutes.File.temporary() as tr:
		idx_path = tr / 'index.xml'
		with idx_path.open('wb') as f:
			f.write(xml)

		for k, r in index.items():
			ek = k.encode('utf-8')
			pek = b'profile:' + ek
			output = formats.route(ek)

			if metrics is not None and metrics.has_key(pek):
				spd = str(metrics.route(pek))
			else:
				spd = ''

			try:
				rtf = xslt.process_file(str(r),
					document_index = str(idx_path),
					reference_suffix = suffix,
					metrics_profile = spd,
				)
			except Exception as err:
				print(k, str(err))
				continue

			if 0:
				deflate = lzma.LZMACompressor()
				with output.open('wb') as f:
					bio = io.BytesIO()
					rtf.write(bio)
					bio.seek(0)
					f.write(deflate.compress(bio.read()))
					f.write(deflate.flush())
			else:
				with output.open('wb') as f:
					rtf.write(f)

if __name__ == '__main__':
	sys.exit(main(*sys.argv[1:]))
