import json
from pathlib import Path
import sys
import unittest
from xml.etree import ElementTree as E
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from export_drawio import export
class DrawioTests(unittest.TestCase):
 def test_native_cells_pages_and_connections(self):
  spec=json.loads((ROOT/'assets/example.architecture.json').read_text())
  root=E.fromstring(export([spec,spec]))
  self.assertEqual(len(root.findall('diagram')),2)
  self.assertNotIn('data:image',E.tostring(root,encoding='unicode'))
  for graph in root.findall('diagram/mxGraphModel'):
   objects={o.attrib['id']:o for o in graph.findall('root/object')}
   self.assertTrue(all(n['id'] in objects for n in spec['nodes']))
   for n in spec['nodes']:
    self.assertEqual(objects[n['id']].attrib['evidence'],n['evidence'])
    self.assertEqual(objects[n['id']].find('mxCell').attrib['vertex'],'1')
   edge=objects['norm_to_attention'].find('mxCell')
   self.assertEqual(edge.attrib['source'],'norm1')
   self.assertEqual(edge.attrib['target'],'attention')
   self.assertEqual(objects['norm1'].find('mxCell').attrib['parent'],'decoder')
 def test_xml_special_characters_remain_editable_text(self):
  spec=json.loads((ROOT/'assets/example.architecture.json').read_text())
  spec['nodes'][0]['label']='维度 < 512 & Q > K'
  xml=E.fromstring(export([spec]))
  obj=next(o for o in xml.iter('object') if o.attrib['id']==spec['nodes'][0]['id'])
  self.assertEqual(obj.attrib['label'],'维度 < 512 & Q > K')
if __name__=='__main__':unittest.main()
