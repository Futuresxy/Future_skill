"""Observable renderer contract tests; no model downloads or third-party dependencies."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MODULE = importlib.util.spec_from_file_location("render_diagram", ROOT / "scripts/render_diagram.py")
renderer = importlib.util.module_from_spec(MODULE)
MODULE.loader.exec_module(renderer)
NS = {"s": "http://www.w3.org/2000/svg"}


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((ROOT / "assets/example.architecture.json").read_text())

    def test_example_has_unique_editable_elements_and_evidence(self):
        root = ET.fromstring(renderer.render(self.spec))
        ids = [e.attrib["id"] for e in root.iter() if "id" in e.attrib]
        self.assertEqual(len(ids), len(set(ids)))
        for obj in self.spec["nodes"] + self.spec["edges"]:
            group = root.find(f"s:g/s:g[@id='{obj['id']}']", NS)
            self.assertIsNotNone(group)
            if obj.get("kind") != "callout":
                self.assertEqual(group.find("s:title", NS).text, obj["evidence"])

    def test_callouts_have_no_arrows_but_computation_does(self):
        root = ET.fromstring(renderer.render(self.spec))
        for e in self.spec["edges"]:
            line = root.find(f"s:g/s:g[@id='{e['id']}']/s:polyline", NS)
            self.assertEqual("marker-end" in line.attrib, e.get("kind") != "callout")

    def test_text_is_escaped_and_remains_literal(self):
        literal = '<script>& "Q < K"'
        self.spec["title"] = literal
        self.spec["nodes"][0]["label"] = literal
        root = ET.fromstring(renderer.render(self.spec))
        self.assertEqual(root.find("s:title", NS).text, literal)
        self.assertEqual(root.findall(".//s:script", NS), [])
        self.assertIn(literal, "".join(root.itertext()))

    def test_unknown_node_and_duplicate_ids_rejected(self):
        for mode in ("missing", "duplicate", "reserved"):
            spec = copy.deepcopy(self.spec)
            if mode == "missing":
                spec["edges"][0]["from"] = "nonexistent"
            elif mode == "duplicate":
                spec["nodes"][0]["id"] = spec["panels"][0]["id"]
            else:
                spec["nodes"][0]["id"] = "arrow"
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                renderer.render(spec)

    def test_out_of_bounds_and_nonfinite_geometry_rejected(self):
        for key, value in (("x", -1), ("w", 2000), ("x", float("nan")), ("h", 0)):
            spec = copy.deepcopy(self.spec)
            spec["nodes"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                renderer.render(spec)

    def test_missing_evidence_rejected(self):
        for kind in ("nodes", "edges"):
            spec = copy.deepcopy(self.spec)
            del spec[kind][0]["evidence"]
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                renderer.render(spec)

    def test_port_connections_end_at_node_boundaries(self):
        self.spec["edges"] = [{"id":"test_ports", "from":"norm1", "to":"attention",
                               "from_port":"top", "to_port":"bottom", "evidence":"fixture"}]
        root = ET.fromstring(renderer.render(self.spec))
        line = root.find("s:g/s:g[@id='test_ports']/s:polyline", NS)
        coordinates = [tuple(map(float,p.split(','))) for p in line.attrib['points'].split()]
        self.assertEqual(coordinates[0], (330,1330))
        self.assertEqual(coordinates[-1], (330,1254))

    def test_cli_invalid_input_does_not_replace_existing_svg(self):
        with tempfile.TemporaryDirectory() as td:
            src, out = Path(td)/"invalid.json", Path(td)/"old.svg"
            src.write_text('{}')
            out.write_text('previous deliverable')
            run = subprocess.run([sys.executable,str(ROOT/'scripts/render_diagram.py'),str(src),'--output',str(out)], capture_output=True, text=True)
            self.assertNotEqual(run.returncode,0)
            self.assertEqual(out.read_text(),'previous deliverable')
            self.assertIn('Missing title',run.stderr)


if __name__ == '__main__':
    unittest.main()
