# AI Desktop Partner

AI Desktop Partner is a Python desktop assistant that uses AI models to generate Python code for everyday PC tasks, coding support, and simple automation.

The application includes a graphical interface where the user can type a command, receive an AI response, view generated Python code, execute the code, save useful commands, and manage command history.

## Features

- Chat-style desktop interface
- Python code generation from natural language commands
- Local LLM support through Ollama
- Cloud model support through Google AI API
- Code streaming support
- Separate metadata model for title, icon, response, and risk level
- Generated code display with syntax highlighting
- Execute, copy, save, and cancel buttons
- Saved commands panel
- Command history panel
- Risk level display: Low, Medium, or High
- Auto-run option for low-risk commands
- Settings window for models, API keys, streaming, and extra prompt instructions
- Local storage using JSON files

## Technologies Used

- Python
- CustomTkinter
- Ollama
- Google AI API
- Requests
- JSON
- Threading
- Multiprocessing
- Subprocess
- Pyperclip
- Regular Expressions
  
## Requirements

Before running the project, make sure you have:

- Python 3.10 or newer
- Ollama installed, if you want to use local models
- At least one local Ollama model downloaded
- Internet connection, if you want to use cloud models

## Cloud Model Mode
The application also supports cloud-based AI models through Google AI API.

To use cloud mode, open the settings window and enter:

Cloud API URL
Cloud API Key
Cloud Model Name

Cloud mode requires an internet connection and a valid API key.

Currently Supporting: https://aistudio.google.com


## Installation
### 1. Make sure you have ollama installed with atleast 1 model downloaded. https://ollama.com
```powershell
       #install ollama
       irm https://ollama.com/install.ps1 | iex
       
       #check version
       ollama --version 
       
       #download llama3.2 3B model
       ollama pull llama3.2:3b
       
       #see installed models
       ollama list
```
### 2. Clone the repository
```powershell 
       git clone https://github.com/EdionI/Desktop_AI_Assistant.git
       cd Desktop_AI_Assistant
```
### 3. Install required python libraries: 
```powershell
       #required
       pip install customtkinter requests pyperclip
       #extras
       pip install pyautogui pygetwindow keyboard mouse psutil pillow opencv-python selenium
```
### 4. run main.py
```powershell 
       python main.py
```


