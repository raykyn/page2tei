# page2tei
A python script which converts exported pageXML from Transkribus to valid TEI files.

Developed by Ismail Prada Ziegler on behalf of the University of Zurich and Updated on behalf of the University of Berne.

## Usage

```
usage: page2TEI.py [-h] -i INFOLDER -o OUTFOLDER [--ignore_warnings]

Convert Transkribus exported PageXML files into TEI files.

optional arguments:
  -h, --help            show this help message and exit
  -i INFOLDER, --infolder INFOLDER
                        Path to folder with the files to process. If you
                        exported from Transkribus just pass the path to the
                        exported folder (unzipped).
  -o OUTFOLDER, --outfolder OUTFOLDER
                        Path to the folder where the TEI files should be
                        stored. Mind you all files found in the infolder will
                        be saved as TEIs to that folder directly, the folder
                        hierarchy of the input format will not be copied.
  --ignore_warnings     Ignore warnings, e.g. thrown when an abbreviation was
                        annotated but no expansion attribute was given
```

## Requirements
- Python 3.8 or newer (should also work with other 3.X but was not tested)
- External Python module `lxml` (https://lxml.de/)

## Notes
- tag_deepness.json manages in which order tags that cover exactly the same span of characters are sorted. For example we might always want del-tags to be contained by sic-tags. We cannot do this automatically, because this can be different for each project. The current file should be viewed as an example and I strongly recommend you make your own hierarchy which fits your needs. Note that if any tags are not contained in the json-file, they will be assigned the next higher number. This prevents errors but might not produce the behavior you wish for, so make sure to include all of your tags there. You can edit this file with any kind of text editor.
- tag_name_conversion.json contains a dictionary which informs the program how to translate certain tags. Tags not included will stay the same. The current file should be viewed as an example but already contains typical conversions e.g. "person" => "persName".
- The program will inform you if any of the produced XML are not valid. This may happen for example if there were overlapping tags assigned in Transkribus, something XML can hardly reproduce. Note that the program always only shows you the first error it encounters per file, so you will have to run it again to see if there is another error. You may uncomment line 253 to activate the validation for each line in your file separately, which will show you all errors in the same run. Make sure to read the note I wrote next to it, which is why it's not activated per default.
- The TextStyle-tag is handled in a very project-specific way and you might want to change the conversion behavior for this tag for your project. Look into the insert_attributes-function to change it. 
- The date-tag at the moment uses a standard day-month-year format in the "when"-attribute. Your project might want to handle this differently, look into the insert_attributes-function to change its behavior.
- Note that this script was developed for very specific use in context of the edition project Königsfelden (https://www.koenigsfelden.uzh.ch/) and we can not be aware of any needs your project has. Feel welcome to ask for features and help in the "Issues"-tab on Github.

## Contact
Please report bugs and request features via the Issues-tab on Github.

In case of further questions, you may contact me at ismail.prada@unibe.ch.
