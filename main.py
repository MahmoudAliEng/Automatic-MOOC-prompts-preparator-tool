
from bs4 import BeautifulSoup
import re
import requests
import fitz  
from os import remove, listdir
from argparse import ArgumentParser


def read_html_file(file_path: str) -> str:
    '''Reads the content of an html file and returns it as a string'''

    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def download_pdf_and_extract_text(url: str, filename: str) -> str:
    '''Downloads a pdf file from a url, extracts the text from it, clean it then returns it'''
    
    response = requests.get(url)
    with open(filename, 'wb') as pdf_file:
        pdf_file.write(response.content)

    doc = fitz.open(filename)
    pdf_text = ""
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        pdf_text += page.get_text()

    pdf_text = pdf_text.replace('septembre 2018', '')
    pdf_text = re.sub(r'MOOC « Éthique de la recherche(\s)*»', '', pdf_text)
    pdf_text = re.sub(r'Module \d - Séquence  \d \n', '', pdf_text)
    pdf_text = re.sub(r'(\n\s*){2,}', '', pdf_text)
    doc.close()

    remove(filename)
    return pdf_text.strip()

def extract_questions_answers(soup : BeautifulSoup, 
                              fr: bool=True) -> dict:
    '''Extracts the questions and answers from the html content and returns them as a dictionary indexed by the section id'''
    
    questions = {}
    quiz_sections = soup.find_all('div', class_='problems-wrapper')

    for quiz_index, quiz_section in enumerate(quiz_sections, start=1):
        question_section_id = get_question_section_id(quiz_section)
        question_blocks = quiz_section.find_all('p')
        questions_answers = extract_questions_from_section(question_blocks, fr)
        questions_answers = "\n".join(questions_answers)
        questions[question_section_id] = questions_answers
    
    return questions

def get_question_section_id(quiz_section: BeautifulSoup) -> str:
    '''Extracts the question section id from the quiz section'''

    question_section_id = quiz_section.find_all('h2', class_='problem-header')[0].text
    question_section_id = re.search(r'M\d{1}S[1-9]{1}[A-D]{1}', question_section_id,  re.IGNORECASE
                     ).group()
    return question_section_id.upper()

def extract_questions_from_section(question_blocks: list, fr: bool=True) -> list:
    '''Extracts the questions and answers from the question blocks and returns them as a list of formatted strings'''

    questions_answers = []
    for question_index, question_block in enumerate(question_blocks, start=1):
        question_text = extract_question_text(question_block, fr)
        answers_text = extract_answers_text(question_block, fr)
        formatted_qa = format_question_answer( question_index, question_text, answers_text)
        questions_answers.append(formatted_qa)
    return questions_answers

def extract_question_text(question_block: BeautifulSoup, fr: bool=True) -> str:
    '''Extracts the question text from the question block'''

    if fr:
        question_block = question_block.get_text(separator="\n").split('/')[0].strip()
    else:
        question_block = question_block.get_text(separator="\n").split('/')[1].strip()
    question_block = re.sub(r'\n+', '', question_block)
    question_block = re.sub(r'\s{2,}', ' ', question_block)
    return question_block
        
def extract_answers_text(question_block : BeautifulSoup, fr: bool=True) -> list:
    '''Extracts the answers text from the question block'''

    answers = question_block.find_next('fieldset').find_all('label')
    answers_text = []
    for answer in answers:
        if fr:
            new_answer = answer.get_text(separator="\n").split('/')[0].strip()
            new_answer = re.sub(r'\n+', '', new_answer)
            new_answer = re.sub(r'\s{2,}', ' ', new_answer)
        else:
            new_answer = answer.get_text(separator="\n").split('/')[1].strip()
            new_answer = re.sub(r'\n+', '', new_answer)
            new_answer = re.sub(r'\s{2,}', ' ', new_answer)
        answers_text.append(new_answer)

    return answers_text

def format_question_answer(question_index: int, question_text: str, answers_text: list) -> str:
    '''Formats the question and answers into a string'''

    answers_indexes = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    answers_text = [f"{answers_indexes[i]}. {ans}" for i, ans in enumerate(answers_text)]
    # return f"{quiz_index}.{question_index} {question_text}\n" + f"\n".join(answers_text)
    return f"{question_index} {question_text}\n" + f"\n".join(answers_text)

def create_prompt(cleaned_text: str, qa_pairs: str, fr: bool=True) -> str:
    '''Creates a prompt from the cleaned text and the questions and answers pairs'''

    if fr:
        prompt = f"à partir ce texte \"{cleaned_text}\" réponds ces questions:\n{qa_pairs}"
    else:
        prompt = f"from this text \"{cleaned_text}\" answer these questions:\n{qa_pairs}"
    return prompt

def save_prompt(moocer_ref: str, prompt: str) -> None:
    '''Saves the prompt to a text file'''

    with open(f"{moocer_ref}.txt", 'w', encoding='utf-8') as f:
        f.write(prompt)

def process_html_file(html_content: str) -> None:
    '''Processes the html content and creates the prompt files'''

    soup = BeautifulSoup(html_content, 'html.parser')
    moocer_sections = soup.find_all('h2', string=re.compile(r'MOOCER M[1-9]{1}S[1-9]{1}[A-D]{1}'))

    sections_urls = {}
    fr = True
    for section in moocer_sections:
        section_id = re.search(r'M\d{1}S[1-9]{1}[A-D]{1}', section.text.strip()).group()
        if section_id not in sections_urls:
            matching_tags = soup.find_all("a", href=re.compile(rf"{section_id}.*(?<!_EN)\.pdf$", re.IGNORECASE))
            if not matching_tags:
                matching_tags = soup.find_all("a", href=re.compile(rf"{section_id}.*\.pdf$", re.IGNORECASE))
                fr = False
            for tag in matching_tags:
                print(f"-----Section {section_id}")
                sections_urls[section_id] = 'https://lms.fun-mooc.fr'+tag['href']
                transcript = download_pdf_and_extract_text(sections_urls[section_id], f"moocer_pdfs/{section_id}.pdf")
                questions = extract_questions_answers(soup)
                qa_pairs = questions[section_id]
                prompt = create_prompt(transcript, qa_pairs, fr)
                save_prompt(f'moocer_prompts/{section_id}', prompt)

def remove_prompt_files(prompt_dir: str='moocer_prompts') -> None:
    '''Removes all prompt files'''
    
    files = listdir(prompt_dir)
    for file in files:
        remove(f'{prompt_dir}/{file}')


def main():
    parser = ArgumentParser()
    parser.add_argument('-d', action='store_true', help='Remove all prompt files')
    args = parser.parse_args()
    
    if args.d:
        remove_prompt_files()
        print('Prompt files removed')
    else:
        html_content = read_html_file('page.html')
        process_html_file(html_content)
        print('Prompt files created')

if __name__ == '__main__':
    main()