"""
# Join delineated source data into a text file for HTML rendering.
"""
import json
import sys

from fault.context import comethod

from fault.system import process
from fault.system import files

from fault.text import render
from fault.text import nodes
from fault.text import document

def get_properties(nodes):
	"""
	# Get the set of unordered list based properties from the &nodes.

	# Returns the number of items present in the initial set found in &nodes,
	# and the set of sole paragraph fragments contained by each item.
	"""
	nitems = 0

	try:
		typ, items, attrs = nodes[0]
		nitems = len(items)

		if typ == 'set':
			return nitems, set([
				f for f in [
					document.export(i[1][0][1]).sole
					for i in items
				]
				if f[0].startswith('literal/') or f[0].startswith('reference/')
			])
	except Exception:
		pass

	return nitems, set()

def interpret_dictionary_items(items):
	return {
		i[2]['identifier']: (nodes.document.export(i[1][0][1]), i[1][1][1])
		for i in items
	}

def get_parameters(rq):
	"""
	# Extract parameters from a documentation string.
	"""
	params = rq.select('/section[Parameters]/dictionary/item')
	return interpret_dictionary_items(params)

def extract(prefix, sub):
	r, = sub.root
	params = get_parameters(sub)
	depth = len(prefix) - 1

	for i, x in enumerate(r[1]):
		if (x[0], x[2]['identifier']) == ('section', 'Parameters'):
			del r[1][i]

	stack = [x for x in r[1] if x[0] == 'section']
	while stack:
		subsections = []
		for section in stack:
			# Prefix with empty path.
			sd = section[2]
			a = sd['absolute']
			a = prefix + tuple(a or ())
			sd['absolute'] = a

			# Adjust depth to always be relative.
			sd['selector-multiple'] = None
			sd['selector-level'] = len(sd['absolute']) - 1
			sd['selector-path'] = sd['absolute'][-1:]

			subsections.extend([x for x in section[1] if x[0] == 'section'])
		depth += 1
		stack = subsections

	return r, params

def control(**kw):
	"""
	# Construct a CONTROL admonition node.
	"""
	return (
		'admonition', [
			('dictionary', [
				_item(k, v)
				for k, v in kw.items()
			], {})
		],
		{'type': 'CONTROL'}
	)

class Text(comethod.object):
	"""
	# Materialization routines for source elements.
	"""

	def r_control(self, node):
		return [
			"! CONTROL:\n",
			"\t/type/\n",
			"\t\t" + node[0] + "\n",
		]

	@comethod('class')
	def r_container(self, path, node):
		yield self.newline
		yield self.section(0, None, path)
		yield from self.r_control(node)

		doc = self.docs.get(path, None)
		if doc:
			sub = nodes.Cursor.from_chapter_text('\n'.join(doc))
			r, params = extract(path, sub)
			if params:
				sect = r[1][0]
				pd = ('dictionary', [], {})
				sect[1].append(pd)
				for i in self.r_parameters(param_ids, params):
					pd[1].append(i)

			for x in r[1]:
				yield from render.tree(x)

		yield from self.switch(path, node[1])

	def r_parameters(self, nodes, params):
		for nid, n in nodes:
			v_content = []

			i = ('item', [
				('key', ["(parameter)`%s`"%(nid,)], {}),
				('value', v_content, {}),
			], {'identifier': nid})

			if nid in params:
				k, v = params[nid]

				print('...', n, file=sys.stderr)
				nprops, props = get_properties(v)
				if len(props) == nprops:
					del v[:1]
					for p in props:
						print('property', p, file=sys.stderr)
						#append(["\t", "-", " ", render.inline_fragment(p), "\n"])

				v_content.extend(v)
				if nid == 'signal':
					print('<---', v_content, file=sys.stderr)
			else:
				i[1][1][1].append((
					'paragraph', [
						('literal', ['Undocumented'], {'cast': 'ctl/absent'}),
						'.'
					], {}
				))

			yield i

	def section(self, rdepth, rmult, path):
		p = render.section_path(rdepth, rmult, *path)
		p.append("\n")
		return "".join(p)

	@comethod('data')
	def r_data(self, path, node):
		yield self.newline
		yield self.section(0, None, path)

		yield from self.r_control(node)

		sig = "(signature)`%s`" % (path[-1],)
		sig += " (data/equality)`=` "

		de = self.data.get(path, None)
		if isinstance(de, dict):
			yield sig + "(syntax)`%s`\n" %(de['syntax'],) + self.newline
		else:
			yield sig + "`%s`" %(repr(de),) + self.newline

	@comethod('method')
	@comethod('function')
	def r_function(self, path, node):
		yield self.newline
		yield self.section(0, None, path)

		yield from self.r_control(node)

		param_ids = []
		for n in node[1]:
			if n[0] not in {'type',}:
				param_ids.append((n[2]['identifier'], n))

		sig = "(signature)`%s(%s)`" % (path[-1], ", ".join(x[0] for x in param_ids))
		sig += self.newline
		yield sig
		# Break for paragraph.
		yield self.newline

		doc = self.docs.get(path, None)
		if doc:
			sub = nodes.Cursor.from_chapter_text('\n'.join(doc))
			r, params = extract(path, sub)
			sect = r[1][0]
			pd = ('dictionary', [], {})
			sect[1].append(pd)
			for i in self.r_parameters(param_ids, params):
				pd[1].append(i)
		else:
			params = {}
			r = ('chapter', [], {})

		for x in r[1]:
			yield from render.tree(x)

	def switch(self, path, nodes, *suffix):
		for x in nodes:
			try:
				method = self.comethod(x[0], *suffix)
				p = path + (x[2].get('identifier'),)
				yield from method(p, x)
			except comethod.MethodNotFound:
				pass

	def __init__(self, elements, docs, data):
		self.newline = "\n"
		self.elements = elements
		self.docs = docs
		self.data = data

def main(inv:process.Invocation) -> process.Exit:
	import sys
	source, *metas = inv.args
	r = files.Path.from_path(source)
	re = (r/"elements.json")
	dd = (r/"documented.json")
	rd = (r/"documentation.json")
	rt = (r/"data.json")

	with re.fs_open('r') as f:
		elements = json.load(f)

	with dd.fs_open('r') as f:
		keys = json.load(f)
	with rd.fs_open('r') as f:
		strings = json.load(f)
	docs = dict(zip(map(tuple,keys),strings))

	with rt.fs_open('r') as f:
		keys, datas = json.load(f)
		data = dict(zip(map(tuple,keys),datas))

	t = Text(elements, docs, data)
	sys.stdout.writelines(t.switch((), elements[1]))

	return inv.exit(0)

if __name__ == '__main__':
	process.control(main, process.Invocation.system())