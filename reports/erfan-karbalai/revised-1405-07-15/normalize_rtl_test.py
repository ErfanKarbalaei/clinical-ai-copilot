from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as ET
import re, shutil

W="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
SRC=Path(__file__).resolve().parent/"گزارش_پروژه_کارشناسی_عرفان_کربلائی_با_تقدیم_و_سپاسگزاری.docx"
OUT=Path(__file__).resolve().parent/"qa-pages"/"rtl-test.docx"
shutil.copy2(SRC,OUT)
LTR=re.compile(r"[A-Za-z][A-Za-z0-9_.:/{}?=+\-]*")
def q(tag): return W+tag
with ZipFile(OUT,"r") as z:
    blobs={n:z.read(n) for n in z.namelist()}
styles=ET.fromstring(blobs["word/styles.xml"])
style_center=set()
for st in styles.iter(q("style")):
    sid=st.get(q("styleId")); jc=st.find(f"{q('pPr')}/{q('jc')}")
    if sid and jc is not None and jc.get(q("val"))=="center": style_center.add(sid)
for name,data in list(blobs.items()):
    if not (name=="word/document.xml" or (name.startswith("word/header") or name.startswith("word/footer")) and name.endswith(".xml")):
        continue
    root=ET.fromstring(data)
    for p in root.iter(q("p")):
        ppr=p.find(q("pPr"))
        if ppr is None:
            ppr=ET.Element(q("pPr")); p.insert(0,ppr)
        oldjc=ppr.find(q("jc"))
        pstyle=ppr.find(q("pStyle"))
        centered=(oldjc is not None and oldjc.get(q("val"))=="center") or (pstyle is not None and pstyle.get(q("val")) in style_center)
        if oldjc is None:
            oldjc=ET.SubElement(ppr,q("jc"))
        oldjc.set(q("val"),"start")
        bidi=ppr.find(q("bidi"))
        if bidi is None: bidi=ET.SubElement(ppr,q("bidi"))
        bidi.set(q("val"),"1")
        if centered:
            tabs=ppr.find(q("tabs"))
            if tabs is None: tabs=ET.SubElement(ppr,q("tabs"))
            if not any(x.get(q("val"))=="center" for x in tabs.findall(q("tab"))):
                tab=ET.SubElement(tabs,q("tab")); tab.set(q("val"),"center"); tab.set(q("pos"),"4536")
            runs=p.findall(q("r"))
            if runs and runs[0].find(q("tab")) is None:
                tabrun=ET.Element(q("r")); rpr=ET.SubElement(tabrun,q("rPr")); rtl=ET.SubElement(rpr,q("rtl")); rtl.set(q("val"),"1")
                ET.SubElement(tabrun,q("tab")); p.insert(list(p).index(runs[0]),tabrun)
        for run in p.iter(q("r")):
            texts=list(run.iter(q("t")))
            if not texts: continue
            rpr=run.find(q("rPr"))
            if rpr is None:
                rpr=ET.Element(q("rPr")); run.insert(0,rpr)
            rtl=rpr.find(q("rtl"))
            if rtl is None: rtl=ET.SubElement(rpr,q("rtl"))
            rtl.set(q("val"),"1")
            lang=rpr.find(q("lang"))
            if lang is None: lang=ET.SubElement(rpr,q("lang"))
            lang.set(q("val"),"fa-IR"); lang.set(q("eastAsia"),"fa-IR")
            for t in texts:
                s=t.text or ""
                if "۱۵ اکتبر ۲۰۲۶" in s and "\u202a" not in s:
                    t.text="\u202a"+s+"\u202c"
                elif re.search(r"[A-Za-z]",s) and "\u202a" not in s:
                    t.text=LTR.sub(lambda m:"\u202a"+m.group(0)+"\u202c",s)
    for tbl in root.iter(q("tbl")):
        tblpr=tbl.find(q("tblPr"))
        if tblpr is None:
            tblpr=ET.Element(q("tblPr")); tbl.insert(0,tblpr)
        bidi=tblpr.find(q("bidiVisual"))
        if bidi is None: bidi=ET.SubElement(tblpr,q("bidiVisual"))
        bidi.set(q("val"),"1")
    blobs[name]=ET.tostring(root,encoding="utf-8",xml_declaration=True)
with ZipFile(OUT,"w",ZIP_DEFLATED) as z:
    for name,data in blobs.items(): z.writestr(name,data)
print(OUT)
