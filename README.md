# Automatic MOOC prompts preparator tool

This tool is designed to help you prepare prompts for a specific MOOC at FUN. It extracts links (to download specific PDF files and get a cleaned text), questions and answers for each video in the HTML MOOC page. Then it prepare formatted prompt text file for each section in the MOOC page.

## Installation

1. Clone the repository
1. download the whl file for PyMuPDF library from [here](https://pypi.org/project/PyMuPDF/#files) according to your system
   and install it using `pip install <path_to_whl_file>`
1. Install the requirements: `pip install -r requirements.txt`
1. Run the tool: `python main.py` (pass *-d* if you want just deleting prompt files)