#!/usr/bin/env python3
"""Export architecture JSON pages to native, individually editable draw.io cells."""
import argparse
import json
from pathlib import Path
from xml.etree import ElementTree as E
from render_diagram import validate, color, port


def export(specs):
    file = E.Element('mxfile', host='app.diagrams.net', type='device', compressed='false')
    for page_no, spec in enumerate(specs, 1):
        nodes = validate(spec)
        page = E.SubElement(file, 'diagram', id=f'page-{page_no}', name=spec.get('page_name', spec['title']))
        graph = E.SubElement(page, 'mxGraphModel', dx='0', dy='0', grid='1', gridSize='10', page='1', pageScale='1', pageWidth=str(spec['width']), pageHeight=str(spec['height']), background='#FFFFFF', math='0')
        root = E.SubElement(graph, 'root')
        E.SubElement(root, 'mxCell', id='0')
        E.SubElement(root, 'mxCell', id='1', parent='0')
        used = {o['id'] for k in ('panels','nodes','edges','labels') for o in spec.get(k,[])} | {'0','1'}
        def unique(prefix):
            while prefix in used: prefix += '_'
            used.add(prefix)
            return prefix
        def cell(ident, value, style, box=None, parent='1', evidence=''):
            # UserObject metadata retains evidence in the editor's Edit Data dialog.
            wrapper = E.SubElement(root,'object',id=ident,label=str(value),tooltip=evidence,evidence=evidence)
            c=E.SubElement(wrapper,'mxCell',vertex='1',parent=parent,style=style)
            if box is not None:
                x,y,w,h=box
                E.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
            return c
        base='whiteSpace=wrap;html=0;fontFamily=Arial;strokeWidth=1.5;'
        def text(ident,x,y,value,size=17,align='left',fg='#222222',bold=False):
            lines=str(value).split('\n'); width=max(80,max(len(l) for l in lines)*size*1.1)
            if align=='center': x-=width/2
            elif align=='right': x-=width
            cell(ident,value,base+f'text;strokeColor=none;fillColor=none;align={align};verticalAlign=top;fontSize={size};fontColor={fg};fontStyle={int(bold)};', (x,y-size,width,len(lines)*size*1.35))
        text(unique('title'),spec['width']/2,46,spec['title'],32,'center',bold=True)
        text(unique('source'),spec['width']/2,76,spec['source_note'],15,'center')
        panels=spec.get('panels',[])
        for p in panels:
            cell(p['id'],p.get('label',''),base+f'rounded=1;container=1;collapsible=0;fillColor=none;strokeColor={color(p.get("role","neutral"))};dashed=1;dashPattern=8 5;align=left;verticalAlign=top;spacingLeft=12;spacingTop=6;fontStyle=1;fontSize=22;',tuple(p[k] for k in ('x','y','w','h')))
        for n in nodes.values():
            x,y,w,h=(n[k] for k in ('x','y','w','h')); role=n.get('role','backbone'); c=color(role); shape=n.get('shape','box')
            parents=[p for p in panels if p['x']<=x and p['y']<=y and x+w<=p['x']+p['w'] and y+h<=p['y']+p['h']]
            p=min(parents,key=lambda p:p['w']*p['h']) if parents else None
            fg=color(n['text_color']) if 'text_color' in n else c if shape=='outline' else '#FFFFFF' if role in ('backbone','moe','detail','neutral','cache') else '#202020'
            st=base+f'fillColor={"#FFFFFF" if shape=="outline" else c};strokeColor={c};fontColor={fg};fontSize={n.get("font_size",18)};'
            st+= 'ellipse;' if shape in ('add','multiply') else 'shape=trapezoid;direction='+('south' if shape=='up' else 'north')+';' if shape in ('up','down') else 'rounded=1;arcSize=15;'
            if shape=='outline': st+='dashed=1;dashPattern=8 5;fontStyle=1;'
            cell(n['id'],{'add':'+','multiply':'×'}.get(shape,n.get('label','')),st,(x-(p['x'] if p else 0),y-(p['y'] if p else 0),w,h),p['id'] if p else '1',n['evidence'])
        def terminal(pt):
            for n in nodes.values():
                x,y,w,h=(n[k] for k in ('x','y','w','h')); a,b=pt
                if x-1<=a<=x+w+1 and y-1<=b<=y+h+1 and min(abs(a-x),abs(a-x-w),abs(b-y),abs(b-y-h))<=1:
                    return n['id'], max(0,min(1,(a-x)/w)), max(0,min(1,(b-y)/h))
            return None
        for edge in spec.get('edges',[]):
            pts=edge.get('points')
            if pts is None: pts=[port(nodes[edge['from']],edge.get('from_port','top')),port(nodes[edge['to']],edge.get('to_port','bottom'))]
            kind=edge.get('kind','data'); st=base+f'edgeStyle=none;rounded=0;endArrow={"none" if kind=="callout" else "block"};endFill=1;strokeColor={color(edge.get("role","neutral"))};'
            if kind in ('callout','route','optional'): st+='dashed=1;dashPattern=8 5;'
            attrs={}
            for side,pt in [('source',pts[0]),('target',pts[-1])]:
                t=terminal(pt)
                if t:
                    attrs[side]=t[0]; key='exit' if side=='source' else 'entry'
                    st+=f'{key}X={t[1]};{key}Y={t[2]};{key}Dx=0;{key}Dy=0;{key}Perimeter=0;'
            obj=E.SubElement(root,'object',id=edge['id'],label='',evidence=edge.get('evidence',''),tooltip=edge.get('evidence',''))
            c=E.SubElement(obj,'mxCell',edge='1',parent='1',style=st,**attrs)
            g=E.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'})
            for side,pt in [('source',pts[0]),('target',pts[-1])]:
                if side not in attrs: E.SubElement(g,'mxPoint',x=str(pt[0]),y=str(pt[1]),attrib={'as':side+'Point'})
            if len(pts)>2:
                arr=E.SubElement(g,'Array',attrib={'as':'points'})
                for x,y in pts[1:-1]: E.SubElement(arr,'mxPoint',x=str(x),y=str(y))
            if 'label' in edge: text(unique(edge['id']+'_label'),edge['label_x'],edge['label_y'],edge['label'],edge.get('font_size',15),{'start':'left','middle':'center','end':'right'}.get(edge.get('anchor','start')))
        for t in spec.get('labels',[]):
            text(t['id'],t['x'],t['y'],t['text'],t.get('font_size',16),{'start':'left','middle':'center','end':'right'}[t.get('anchor','start')],color(t.get('role','neutral')),t.get('bold',False))
    E.indent(file)
    return E.tostring(file,encoding='unicode',xml_declaration=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('inputs',type=Path,nargs='+');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:
        content=export([json.loads(f.read_text(encoding='utf-8')) for f in a.inputs])
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(content,encoding='utf-8')
    except (OSError,ValueError,KeyError,TypeError) as exc: p.exit(1,f'export_drawio: {exc}\n')
    print(a.output)

if __name__=='__main__':main()
