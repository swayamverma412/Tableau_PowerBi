
import pathlib
import textwrap

import google.generativeai as genai

from IPython.display import display
from IPython.display import Markdown

def to_markdown(text):
    text = text.replace('.', ' *')
    return Markdown(textwrap.indent(text,'> ', predicate = lambda _: True))



# %%
import os
from dotenv import load_dotenv, dotenv_values
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


# %%
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)


# %%
model = genai.GenerativeModel('gemini-1.5-flash')


expression = "{DATEDIFF('year', [Birthdate], TODAY()) }"

response = model.generate_content(f"Convert this tableau expression into dax expression. Give me the dax query as output {expression}")
to_markdown(response.text)

