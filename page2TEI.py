#! /usr/bin/python3

"""
This script transforms PageXMLs to TEIs.
python3 pageToTEI.py -i <infolder> -o <outfolder> [--ignore_warnings]

Created by Ismail Prada Ziegler for the Editionsprojekt Königsfelden at the University of Zurich in 2020.
Updated by Ismail Prada Ziegler in 2022 while working for the University of Bern.
"""

from collections import defaultdict
from lxml import etree as et
#from xml.sax.saxutils import escape
from glob import glob
import argparse
import os
#import pprint as pp
import json
import re


DEBUG = True  # Prints filenames of files that get processed
IGNORE_WARNINGS = False

tei_ns = {
    None: "http://www.tei-c.org/ns/1.0",
    "xml": "http://www.w3.org/XML/1998/namespace"
}
page_ns = {
    None: "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance"
}
ns = {
    "ns2": "http://www.w3.org/1999/xlink",
    "ns3": "http://www.loc.gov/METS/",
    None: ""
}

# load external files
tag_name_conversion = json.load(open("tag_name_conversion.json", encoding="utf8"))
tag_deepness = json.load(open("tag_deepness.json", encoding="utf8"))
MAX_DEEPNESS = max(tag_deepness.values())


def iniateTEI():
    root = et.Element("TEI", nsmap=tei_ns)
    teiHeader = et.SubElement(root, "teiHeader")
    facsimile = et.SubElement(root, "facsimile")
    text = et.SubElement(root, "text")
    body = et.SubElement(text, "body")
    return root


def get_tagging(tag_string):
    """
    Get annotations from pageXML line attributes.
    """
    tags_dict = []
    tags = re.findall(r"(\S+?) \{(.*?)\}", tag_string)
    for tag in tags:
        tag_dict = {}
        tag_name = tag[0].strip()
        tag_attribs = tag[1]
        tag_attribs = re.findall(r"(.*?):(.*?);", tag_attribs)
        for attrib in tag_attribs:
            key, value = attrib[0].strip(), attrib[1].strip()
            tag_dict[key] = value
        tags_dict.append((tag_name, tag_dict))
    return tags_dict


def create_facsimile(page, tei, pageNo):
    fac = tei.find("facsimile")
    surface = et.SubElement(fac, "surface", ulx="0", uly="0", lrx=page.get("imageWidth"), lry=page.get("imageHeight"))
    surface.set("{http://www.w3.org/XML/1998/namespace}id", "facs_{}".format(pageNo))
    graphic = et.SubElement(surface, "graphic", url=page.get("imageFilename"), width=page.get("imageWidth"), height=page.get("imageHeight"))

    textregions = page.findall("TextRegion", page_ns)
    for tr in textregions:
        coords = tr.find("Coords", page_ns)
        tr_zone = et.SubElement(surface, "zone", points=coords.get("points"), rendition="TextRegion")
        tr_zone.set("{http://www.w3.org/XML/1998/namespace}id", "facs_{}_{}".format(pageNo, tr.get("id")))
        if "structure" in tr.get("custom"):
            tags = get_tagging(tr.get("custom"))
            for tag, attrib in tags:
                if tag == "structure":
                    tr_zone.set("subtype", attrib["type"])
                    break
            
        for line in tr.findall("TextLine", page_ns):
            coords = line.find("Coords", page_ns)
            l_zone = et.SubElement(tr_zone, "zone", points=coords.get("points"), rendition="Line")
            l_zone.set("{http://www.w3.org/XML/1998/namespace}id", "facs_{}_{}".format(pageNo, line.get("id")))


def get_tag_deepness(tag):
    global MAX_DEEPNESS
    if tag in tag_deepness:
        return tag_deepness[tag]
    else:
        MAX_DEEPNESS += 1
        return MAX_DEEPNESS 


def sort_by_offset(tags):
    out_dict = defaultdict(list)
    for tag, value in tags:
        out_dict[value["offset"]].append((tag, value))
    # sort the values by shorter length
    sorted_dict = {}
    for offset, value in out_dict.items():
        value = sorted(value, key=lambda x: (int(x[1]["length"]), get_tag_deepness(x[0])), reverse=True)
        sorted_dict[offset] = value
    return sorted_dict


def sort_by_endpoint(tags):
    out_dict = defaultdict(list)
    for tag, value in tags:
        out_dict[int(value["offset"])+int(value["length"])].append((tag, value))
    # sort the values by shorter length
    sorted_dict = {}
    for offset, value in out_dict.items():
        value = sorted(value, key=lambda x: (int(x[1]["offset"]), -get_tag_deepness(x[0])), reverse=True)
        sorted_dict[offset] = value
    return sorted_dict


def convert_tag(tag):
    if tag in tag_name_conversion:
        return tag_name_conversion[tag]
    else:
        return tag


def insert_attributes(tag, attributes):
    if tag == "textStyle":
        attribute_string = ""
        # In our project at least textStyle is converted to "hi" tags
        # expand or change this for your respective project!
        for attribute, value in attributes.items():
            if attribute in ["length", "offset", "fontSize", "kerning"]:
                continue
            elif attribute in ["superscript", "strikethrough"] and value == "true":
                attribute_string += ' rend="{}"'.format(attribute)
            elif not IGNORE_WARNINGS:
                print("WARNING: Unknown attributes found in textStyle-Tag! Turn on debug to see which file.")
        return attribute_string

    attribute_string = ""
    for attribute, value in attributes.items():
        if attribute in ["length", "offset", "expansion", "correction"] or \
            (tag == "date" and attribute in ["day", "month", "year"]):
            continue
        value = value.replace("\\u0020", " ")
        attribute_string += ' {}="{}"'.format(attribute, value)

    if tag == "date":
        year = int(attributes["year"]) if "year" in attributes else 1
        month = int(attributes["month"]) if "month" in attributes else 1
        day = int(attributes["day"]) if "day" in attributes else 1
        attribute_string += ' when="{:04d}-{:02d}-{:02d}"'.format(year, month, day)

    return attribute_string


def insert_expansion(attributes):
    if "expansion" not in attributes:
        if not IGNORE_WARNINGS:
            print("WARNING: Missing expansion in abbrev tag! Turn on debug to see which file.")
        return "</abbr><expan></expan>"
    expansion = attributes["expansion"].replace("\\u0020", " ")
    expansion_string = "</abbr><expan>{}</expan>".format(expansion)
    return expansion_string


def insert_correction(attributes):
    if "correction" not in attributes:
        if not IGNORE_WARNINGS:
            print("WARNING: Missing correction in sic tag! Turn on debug to see which file.")
        return "</sic><corr></corr>"
    expansion = attributes["correction"].replace("\\u0020", " ")
    expansion_string = "</sic><corr>{}</corr>".format(expansion)
    return expansion_string


def validateLine(text, location):
    line = "<p>" + text + "</p>"
    try:
        tree = et.fromstring(line)
    except Exception as e:
        print(location)
        print(line)
        print(e)


def create_body(page, tei, pageNo, pageroot):
    body = tei.find(".//body")
    pb = et.SubElement(body, "pb", facs="#facs_{}".format(pageNo), n=pageroot.find(".//TranskribusMetadata", page_ns).get("pageNr"))
    pb.set("{http://www.w3.org/XML/1998/namespace}id", "img_{:04d}".format(pageNo))
    
    textregions = page.findall("TextRegion", page_ns)
    for tr in textregions:
        p = et.SubElement(body, "p", facs="#facs_{}_{}".format(pageNo, tr.get("id")))

        for i, line in enumerate(tr.findall("TextLine", page_ns)):
            lb = et.SubElement(p, "lb", facs="#facs_{}_{}".format(pageNo, line.get("id")), n="N{:03d}".format(i+1))
            unicodenode = line.find("./TextEquiv/Unicode", page_ns)
            if unicodenode is None:
                continue
            plaintext = unicodenode.text
            if not plaintext:  # empty line
                continue
            tags = [(x, y) for x, y in get_tagging(line.get("custom")) if "length" in y and int(y["length"]) > 0]
            tags_without_length = [(x, y) for x, y in get_tagging(line.get("custom")) if "length" in y and int(y["length"]) == 0]
            tags = sorted(tags, key=lambda x: int(x[1]["offset"]))
            tags_without_length = sort_by_offset(tags_without_length)
            tags_by_offset = sort_by_offset(tags)
            tags_by_endpoint = sort_by_endpoint(tags)
            tagged_text = ""
            for pos in range(len(plaintext)+1):  # + 1 is necessary to generate tags that are after all characters
                for index, tags_at_index in tags_by_endpoint.items():
                    if int(index) == pos:
                        for t, att in tags_at_index:
                            if t == "sic":
                                tagged_text += insert_correction(att)
                            if t == "abbrev":
                                tagged_text += insert_expansion(att)
                            tagged_text += "</{}>".format(convert_tag(t))

                for index, tags_at_index in tags_by_offset.items():
                    if int(index) == pos:
                        for t, att in tags_at_index:
                            tagged_text += "<{}{}>".format(convert_tag(t), insert_attributes(t, att))
                            if t == "abbrev":
                                tagged_text += "<abbr>"
                            elif t == "sic":
                                tagged_text += "<sic>"
                        #pp.pprint(tags_at_index)

                for index, tags_at_index in tags_without_length.items():
                    if int(index) == pos:
                        for t, att in tags_at_index:
                            tagged_text += "<{}{}/>".format(convert_tag(t), insert_attributes(t, att))

                if pos < len(plaintext):
                    character = plaintext[pos]
                    tagged_text += character

            # Feel free to uncomment this to get all errors in the files at once with context
            # This will also throw an error every time it encounters a sign like "&", "<" and ">" due to some encoding complications.
            # if you manage to fix this, please update the repository
            # validateLine(tagged_text, lb.get("facs"))
            
            lb.tail = tagged_text


def create_head(mets, tei):
    fileDesc = et.SubElement(tei.find("teiHeader"), "fileDesc")

    titleStmt = et.SubElement(fileDesc, "titleStmt")
    title = et.SubElement(titleStmt, "title", type="main")
    title.text = mets.find(".//ns3:amdSec/ns3:sourceMD/ns3:mdWrap/ns3:xmlData/trpDocMetadata/title", ns).text
    principal = et.SubElement(titleStmt, "principal")
    principal.text = mets.find(".//ns3:amdSec/ns3:sourceMD/ns3:mdWrap/ns3:xmlData/trpDocMetadata/uploader", ns).text

    publicationStmt = et.SubElement(fileDesc, "publicationStmt")
    publisher = et.SubElement(publicationStmt, "publisher")
    publisher.text = "tranScriptorium"  # Transkribus specific, change if you used something else

    seriesStmt = et.SubElement(fileDesc, "seriesStmt")
    title = et.SubElement(seriesStmt, "title")
    title.text = mets.find(".//ns3:amdSec/ns3:sourceMD/ns3:mdWrap/ns3:xmlData/trpDocMetadata/collectionList/colList[1]/colName", ns).text
    # WARNING: This code always grabs the title of the FIRST collection it encounters, all others will be ignored

    sourceDesc = et.SubElement(fileDesc, "sourceDesc")
    p = et.SubElement(sourceDesc, "p")
    p.text = "TRP document creator: {}".format(mets.find(".//ns3:amdSec/ns3:sourceMD/ns3:mdWrap/ns3:xmlData/trpDocMetadata/uploader", ns).text)


def convert(infile):
    tree = et.parse(infile)
    root = tree.getroot()
    tei = iniateTEI()
    create_head(root, tei)
    files = root.findall(".//ns3:fileGrp/ns3:file/ns3:FLocat", ns)
    for i, f in enumerate(files):
        filelocation = f.get("{http://www.w3.org/1999/xlink}href")
        pagetree = et.parse(os.path.join(os.path.dirname(infile), filelocation))
        root = pagetree.getroot()
        page = root.find("Page", page_ns)
        create_facsimile(page, tei, i+1)
        create_body(page, tei, i+1, root)
    return tei


def solve_signs(tei):
    tei = re.sub("&lt;", "<", tei)
    tei = re.sub("&gt;", ">", tei)
    tei = re.sub("<lb", "\n        <lb", tei)  # very ugly, but it does the job
    return tei


def main():
    global IGNORE_WARNINGS
    parser = argparse.ArgumentParser(description='Convert Transkribus exported PageXML files into TEI files.')
    parser.add_argument('-i', '--infolder', help='Path to folder with the files to process. If you exported from Transkribus just pass the path to the exported folder (unzipped).', required=True)
    parser.add_argument('-o', '--outfolder', help='Path to the folder where the TEI files should be stored. Mind you all files found in the infolder will be saved as TEIs to that folder directly, the folder hierarchy of the input format will not be copied.', required=True)
    parser.add_argument('--ignore_warnings', help='Ignore warnings, e.g. thrown when an abbreviation was annotated but no expansion attribute was given.', action="store_true", default=False)
    args = parser.parse_args()

    IGNORE_WARNINGS = args.ignore_warnings

    infiles = glob(os.path.join(args.infolder, "**/mets.xml"), recursive=True)
    for infile in infiles:
        if DEBUG:
            print(infile)
        tei = et.ElementTree(convert(infile))
        # By converting to string and replacing the signs ourselves, we get a much more readable output format
        tei = et.tostring(tei, encoding="utf8", pretty_print=True).decode("utf8")
        tei = solve_signs(tei)

        # Notify in case of invalid xml files
        try:
            et.fromstring(tei)
        except Exception as e:
            print("INVALID XML:", e)

        #if not os.path.isdir(os.path.join(sys.argv[2], os.path.dirname(infile).split("/")[1])):
        #    os.mkdir(os.path.join(sys.argv[2], os.path.dirname(infile).split("/")[1]))
        with open(os.path.join(args.outfolder, os.path.split(os.path.dirname(infile))[1] + ".xml"), mode="w", encoding="utf8") as outf:
            outf.write(tei)


if __name__ == "__main__":
    main()
