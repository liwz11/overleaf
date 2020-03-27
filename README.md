# overleaf
A script tool to access overleaf.

### Dependencies

```
requests, websocket, json, bs4, argparse
```

### Usage

```
liwz11@ubuntu:~/overleaf$ python3 overleaf.py -h
usage: overleaf.py [-h] [--logout] [--projects] [--project PROJECT] [--docs]
                   [--doc DOC] [--down DOWN] [--url URL]

A script tool to access www.overleaf.com.

optional arguments:
  -h, --help         show this help message and exit
  --logout           clear cookies and remove csrf token
  --projects         list all available projects
  --project PROJECT  specify a project id, default ''
  --docs             list all .tex documents in the specified project
  --doc DOC          specify a document id, default null(meaning the main document)
  --down DOWN        specify a file type and download the file, default 'pdf',
                     options: 'pdf', 'zip', 'bbl'
  --url URL          specify a url to directly download the target file, default ''
 
```

### Example 1 - list all available projects

```
liwz11@ubuntu:~/overleaf$ python3 overleaf.py --projects

[+] loading the project list...

5c349976c042023b1bd97751 A LaTeX Example
5e60cbcf1afbd8000150aec4 ******
5e5612385b881f0001ba1023 ******
......

```

### Example 2 - list all documents in the specified project

```
liwz11@ubuntu:~/overleaf$ python3 overleaf.py --project 5e60cbcf1afbd8000150aec4 --docs

[+] loading the document list...

5e60cbd01afbd8000150aede ******.tex
5e60cbd01afbd8000150aee0 ******.tex
5e60cbd11afbd8000150aee3 ******.tex
......

```

### Example 3 - download a target file by specifying the project id

```
liwz11@ubuntu:~/overleaf$ python3 overleaf.py --project 5e60cbcf1afbd8000150aec4 --down pdf

[+] compiling the project...

[+] downloading the target file...

▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ 3.69MB    

Total Time: 2.69 s

```

### Example 4 - download a target file by specifying the url

```
liwz11@ubuntu:~/overleaf$ python3 overleaf.py --url "https://www.overleaf.com/download/project/5e60cbcf1afbd8000150aec4/build/1711dbeca03-dbd3e44a305f01b0/output/output.pdf?compileGroup=standard&clsiserverid=clsi-pre-emp-n1-b-2565&popupDownload=true"

[+] downloading the target file...

▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ 3.79MB    

Total Time: 2.51 s

```


