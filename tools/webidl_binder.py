
import os, sys

import shared

sys.path.append(shared.path_from_root('third_party'))
sys.path.append(shared.path_from_root('third_party', 'ply'))

import WebIDL

input_file = sys.argv[1]
output_base = sys.argv[2]

p = WebIDL.Parser()
p.parse(open(input_file).read())
data = p.finish()

interfaces = {}
implements = {}

for thing in data:
  if isinstance(thing, WebIDL.IDLInterface):
    interfaces[thing.identifier.name] = thing
  elif isinstance(thing, WebIDL.IDLImplementsStatement):
    implements.setdefault(thing.implementor.identifier.name, []).append(thing.implementee.identifier.name)

print interfaces
print implements

gen_c = open(output_base + '.cpp', 'w')
gen_js = open(output_base + '.js', 'w')

gen_c.write('extern "C" {\n')

gen_js.write('''
// Bindings utilities

var Object__cache = {}; // we do it this way so we do not modify |Object|
function wrapPointer(ptr, __class__) {
  var cache = Object__cache;
  var ret = cache[ptr];
  if (ret) return ret;
  __class__ = __class__ || Object;
  ret = Object.create(__class__.prototype);
  ret.ptr = ptr;
  ret.__class__ = __class__;
  return cache[ptr] = ret;
}
Module['wrapPointer'] = wrapPointer;

function castObject(obj, __class__) {
  return wrapPointer(obj.ptr, __class__);
}
Module['castObject'] = castObject;

Module['NULL'] = wrapPointer(0);

function destroy(obj) {
  if (!obj['__destroy__']) throw 'Error: Cannot destroy object. (Did you create it yourself?)';
  obj['__destroy__']();
  // Remove from cache, so the object can be GC'd and refs added onto it released
  delete Object__cache[obj.ptr];
}
Module['destroy'] = destroy;

function compare(obj1, obj2) {
  return obj1.ptr === obj2.ptr;
}
Module['compare'] = compare;

function getPointer(obj) {
  return obj.ptr;
}
Module['getPointer'] = getPointer;

function getClass(obj) {
  return obj.__class__;
}
Module['getClass'] = getClass;

// Converts a value into a C-style string.
function ensureString(value) {
  if (typeof value == 'number') return value;
  return allocate(intArrayFromString(value), 'i8', ALLOC_STACK);
}

''')

for name, interface in interfaces.iteritems():
  gen_js.write('// ' + name + '\n')
  #print name, dir(interface)
  args = ''
  body = ''
  cons = interface.getExtendedAttribute('Constructor')
  if type(cons) == list:
    args_list = cons[0]
    for i in range(len(args_list)):
      arg = args_list[i]
      if arg.optional:
        body += '  if (' + arg.identifier.name + ' === undefined) { this.ptr = _emscripten_bind_%s_%d(%s); return }\n' % (name, i, args)
      if len(args) > 0: args += ', '
      args += arg.identifier.name
  else:
    args_list = []
  body += '  this.ptr = _emscripten_bind_%s_%d(%s);\n' % (name, len(args_list), args)
  gen_js.write(r'''
function %s(%s) {
%s
}
%s.prototype = {};

''' % (name, args, body, name))

gen_c.close()
gen_js.close()
