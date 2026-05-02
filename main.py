import multiprocessing
import json
from customtkinter import *
import requests
import json
import threading
import keyword
import re
import subprocess
import pyperclip
# "#080d18"  # background
# "#0d1424"  # big panels
# "#111a2e"  # cards/front panels
# "#26324a"  # borders
# "#8b5cf6"  # purple accent
# "#e5e7eb"  # main text
# "#94a3b8"  # muted text
# "request_name": result.get("request_name", "Untitled Request"),
# "code": result.get("code", ""),
# "risk": result.get("risk", ""),
# "response": result.get("response", ""),
# "icon": result.get("icon", "")

#saved = ["id", "request_name", "code", "risk", "response", "icon"]


SAVE_FILE = "saved.json"

History = []
Saved = []
ConvoHistory = []


def load_saved():
    global Saved

    if not os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "w") as f:
            json.dump([], f, indent=4)

    try:
        with open(SAVE_FILE, "r") as f:
            Saved = json.load(f)

    except Exception:
        Saved = []

    return Saved

def update_saved():
    global Saved
    with open("saved.json", "w") as f:
        json.dump(Saved, f, indent=4)

load_saved()
#print(load_saved())

def extract_json(text: str) -> dict:
    text = text.strip()

    # remove markdown fences if model adds them anyway
    text = text.replace("```json", "").replace("```", "").strip()

    # find JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model response.")

    json_text = match.group(0)
    return json.loads(json_text)


def model(user_request, max_tokens=2000, temperature=0.1, model= ""):
    print(model)
    global History,ConvoHistory,getCodeSpace
    #MODEL = "hf.co/mradermacher/DeepSeek-R1-Distill-Qwen-7B-Uncensored-i1-GGUF:latest" "llama3.1" "qwen3"
    URL = "http://localhost:11434/api/generate"
    history_text = "\n".join(ConvoHistory[-5:])


    SYSTEM = (
        "You are a Python code generator for a desktop assistant app.\n"
        "Your job is to convert the user's request into a structured JSON response.\n\n"

        "OUTPUT RULES:\n"
        "- Output ONLY valid JSON.\n"
        "- Do NOT output markdown.\n"
        "- Do NOT use backticks.\n"
        "- Do NOT explain anything outside the JSON.\n"
        "- Do NOT put Python code as a JSON key.\n"
        "- The JSON must contain exactly these keys: icon, request_name, response, code, risk.\n\n"

        "JSON FORMAT:\n"
        "{\n"
        '  "icon": "emoji icon",\n'
        '  "request_name": "short task title",\n'
        '  "response": "short assistant response",\n'
        '  "code": "valid python code here",\n'
        '  "risk": "Low"\n'
        "}\n\n"

        "FIELD RULES:\n"
        "- icon must be one relevant emoji only, like 🌐, 🖱️, 📝, 📁, 🔍, 🧮, ⚙️, 📸, or 🗑️.\n"
        "- request_name must NOT include an icon.\n"
        "- request_name must be a short title based on the user request, maximum 25 characters.\n"
        "- response must be a short natural sentence describing what the assistant is doing.\n"
        "- response should sound like the assistant is performing the task.\n"
        "- response must not explain the code itself.\n"
        "- response should be under 80 characters when possible.\n"
        "- code must be valid Python code stored as a JSON string.\n"
        "- code must include all required imports.\n"
        "- code must not contain markdown, explanations, or comments unless comments are useful inside the code.\n"
        "- risk must be only one of these: Low, Medium, or High.\n\n"

        "RISK RULES:\n"
        "- risk Low = safe action, like opening a website or app.\n"
        "- risk Medium = medium action, like moving mouse, typing, creating files, or using automation.\n"
        "- risk High = dangerous action, like deleting files, changing system settings, sending emails, or running shell commands.\n\n"

        "EXAMPLES:\n"
        'User request: open google\n'
        'JSON: {"icon":"🌐","request_name":"Open Google","response":"Opening Google.","code":"import webbrowser\\nwebbrowser.open(\\"https://www.google.com\\")","risk":"Low"}\n\n'

        'User request: move my mouse to 10 10\n'
        'JSON: {"icon":"🖱️","request_name":"Move Mouse","response":"Moving mouse to position 10, 10.","code":"import pyautogui\\npyautogui.moveTo(10, 10)","risk":"Medium"}\n\n'

        "IMPORTANT JSON STRING RULES:\n"
        "- New lines inside code must be escaped using \\n.\n"
        "- Double quotes inside code must be escaped using \\\".\n"
        "- The response must be parseable with json.loads().\n"

        "AVAILABLE PYTHON MODULES:\n"
        "- pyautogui for mouse, keyboard, screenshots, and automation.\n"
        "- webbrowser for opening websites.\n"
        "- subprocess for opening applications and shell commands.\n"
        "- os and shutil for file and folder management.\n"
        "- pyperclip for clipboard operations.\n"
        "- pygetwindow for controlling windows.\n"
        "- keyboard for keyboard hotkeys and key presses.\n"
        "- mouse for mouse control and events.\n"
        "- psutil for system and process information.\n"
        "- requests for web requests and APIs.\n"
        "- pillow and cv2 for image processing and screenshots.\n"
        "- selenium for browser automation.\n\n"

        "GENERAL QUESTION RULES:\n"
        "- If the user asks a general knowledge question instead of a desktop action, generate Python code that searches the question on Google.\n"
        "- Use the webbrowser module for Google searches.\n"
        "- Example: if the user asks 'what is the capital of france', open a Google search for that question.\n\n"

        "ENVIRONMENT RULES:\n"
        "- Prefer simple direct solutions over complex multi-step solutions.\n"
        "- When creating files, directly create and write the file using open(..., 'w') when possible.\n"
        "- Avoid unnecessary temporary files, placeholder files, or copy operations.\n"
        "- When opening created text files, prefer default Windows applications like notepad.exe.\n"
        "- Prefer subprocess.Popen([...]) for opening local applications and files.\n"
        "EDITING EXISTING CODE RULES:\n"
        "- If Current CodeSpace contains related code, modify that code instead of recreating from scratch.\n"
        "- If the user asks for more/less/faster/slower, adjust the relevant existing value significantly.\n"
        "- If the user repeats the same request, apply a stronger change than before.\n\n"

        "EXAMPLES:\n"
        'User request: create a text file on desktop called hello.txt\n'
        'JSON: {"icon":"📝","request_name":"Create Text File","response":"Creating a text file on the desktop.","code":"import os\\nimport subprocess\\nfile_path = os.path.expanduser(\\"~/Desktop/hello.txt\\")\\nwith open(file_path, \\"w\\") as f:\\n    f.write(\\"Hello World\\")\\nsubprocess.Popen([\\"notepad.exe\\", file_path])","risk":"Low"}\n\n'
    )

    prompt = (
        f"System: {SYSTEM}\n"
        f"Recent history:\n{history_text}\n\n"
        f"Current Code: \n{getCodeSpace()}\n\n"
        f"User request: {user_request}\n"
        "Assistant JSON:\n"
    )


    response = requests.post(
        URL,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        },
        timeout=60
    )

    response.raise_for_status()

    raw = response.json().get("response", "")
    result = extract_json(raw)

    #History.append(f"User: {user_request}"
    try:
        i = f"{int(History[-1]["ID"])+1}"
    except:
        print("firsthistory?")
        i = len(History)


    History.append({
        "ID": f"{i}",
        "User": f"{user_request}",
        "request_name": f"{result['request_name']}",
        "code": f"{result['code']}",
        "risk": f"{result['risk']}",
        "response": f"{result['response']}",
        "icon": f"{result['icon']}"
    })

    ConvoHistory.append(f"User: {user_request}\nAssistant: {result['response']}\nAssistant Provided Code: {result['code']}\n")






    return {
        "request_name": result.get("request_name", "Untitled Request"),
        "code": result.get("code", ""),
        "risk": result.get("risk", ""),
        "response": result.get("response", ""),
        "icon": result.get("icon", "")
    }






def main():
    global History, current_process,Saved, ConvoHistory,getCodeSpace

    current_process = None
    def getCodeSpace():
        #print(f"got {CodeBox.get("1.0", "end")}")
        return CodeBox.get("1.0", "end")

    def getButtonInfo(id,Type):
        if Type == 0:
            for item in History:
                if item["ID"] == id:

                    insert_to_CodeBox(item["code"],item["ID"] , True)
        if Type == 1:
            for item in Saved:
                if item["ID"] == id:
                    insert_to_CodeBox(item["code"], item["ID"], True)


    def saved_button(parent, name, saved_id, icon):
        btn = CTkButton(
            parent,
            text=f"{icon}  {name}",
            width=188,
            height=38,
            fg_color="#111a2e",
            hover_color="#2d2258",
            border_width=1,
            border_color="#26324a",
            text_color="#e5e7eb",
            font=("Segoe UI", 12, "bold"),
            corner_radius=7,
            anchor="w",
            command = lambda: getButtonInfo(saved_id,1)
        )
        children = [
            child for child in parent.winfo_children()
            if isinstance(child, CTkButton) and child != btn
        ]

        btn.pack(anchor="w", pady=3, padx=2)

        if children:
            btn.pack_configure(before=children[-1])


        return btn

    def history_button(parent, name, history_id):
        btn = CTkButton(
            parent,
            text=f"◷  {name}",
            width=188,
            height=36,
            fg_color="#0f172a",
            hover_color="#1e293b",
            border_width=1,
            border_color="#1e293b",
            text_color="#e5e7eb",
            font=("Segoe UI", 11),
            corner_radius=7,
            anchor="w",
            command= lambda: getButtonInfo(history_id,0)
        )

        #btn.command_id = history_id

        children = [
            child for child in parent.winfo_children()
            if isinstance(child, CTkButton) and child != btn
        ]
        btn.pack(anchor="w", pady=3, padx=2)

        if children:
            btn.pack_configure(before=children[-1])

        return btn

    def highlight_code():
        code = CodeBox.get("1.0", "end-1c")

        for tag in ["keyword", "string", "function", "comment", "builtin", "number"]:
            CodeBox.tag_remove(tag, "1.0", "end")

        patterns = {
            "comment": r"#.*",
            "string": r"(\".*?\"|\'.*?\')",
            "keyword": r"\b(" + "|".join(keyword.kwlist) + r")\b",
            "function": r"\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)",
            "number": r"\b\d+(\.\d+)?\b",
            "builtin": r"\b(print|input|open|len|range|str|int|float|list|dict|set)\b",
        }

        for tag, pattern in patterns.items():
            for match in re.finditer(pattern, code):

                if tag == "function":
                    start, end = match.span(1)
                else:
                    start, end = match.span()

                start_index = f"1.0 + {start} chars"
                end_index = f"1.0 + {end} chars"

                CodeBox.tag_add(tag, start_index, end_index)

    def highlight_chat():
        text = ChatBox.get("1.0", "end-1c")

        for tag in ["user", "bot", "success", "link", "time"]:
            ChatBox.tag_remove(tag, "1.0", "end")

        patterns = {
            "user": r"\buser\b",
            "bot": r"\bbot\b",
            "success": r"✓.*",
            "link": r"https?://[^\s]+",
            "time": r"\b\d{1,2}:\d{2}\b",
        }

        for tag, pattern in patterns.items():
            for match in re.finditer(pattern, text):
                start, end = match.span()

                start_index = f"1.0 + {start} chars"
                end_index = f"1.0 + {end} chars"

                ChatBox.tag_add(tag, start_index, end_index)

    def insert_to_ChatBox(text):
        ChatBox.configure(state="normal")
        ChatBox.insert(END, text)
        ChatBox.see("end")
        highlight_chat()
        ChatBox.configure(state="disabled")

    def insert_to_CodeBox(text,history_id , clear= False):
        if clear:
            CodeBox.delete("1.0", END)
        CodeBox.history_id = history_id
        CodeBox.insert(END, text)

        highlight_code()

    def clear_chat():
        global ConvoHistory
        if ChatBox.get("1.0", "end-1c") != "":
            ConvoHistory = []
            ChatBox.configure(state="normal")
            ChatBox.delete("1.0", "end")
            ChatBox.configure(state="disabled")
            insert_to_ChatBox("bot: Cleared Chat. How can I help you?\n")


    def send():
        user_text = input_entry.get().strip()

        if user_text == "":
            return

        input_entry.delete(0, END)

        insert_to_ChatBox(f"user: {user_text}\n")


        send_btn.configure(state="disabled")
        status.configure(text="●  Status:  Generating...", text_color="#facc15")

        thread = threading.Thread(
            target=run_model_thread,
            args=(user_text,),
            daemon=True
        )
        thread.start()

    def run_model_thread(user_text):
        try:
            result = model(user_text,int(maxTokensEntry.get()), float(temperatureEntry.get()), ModelMenu.get())

            root.after(0, lambda: show_model_result(result))

        except Exception as e:
            try:
                insert_to_ChatBox(f"bot: Model error, {e}\n")
                root.after(0, lambda: show_model_error(e))

            except:
                insert_to_ChatBox(f"bot: Model error")
                root.after(0, lambda: show_model_error("ERROR"))


    def execute_command():

        def check_process_finished():
            global current_process

            if current_process and current_process.is_alive():
                root.after(500, check_process_finished)
            else:
                current_process = None
                ExecuteBtn.configure(state="normal", text="▶  Execute")
                CancelBtn.configure(state="disabled")

        global current_process

        code = CodeBox.get("1.0", "end-1c").strip()

        if code == "":
            return

        if current_process and current_process.is_alive():
            return

        ExecuteBtn.configure(state="disabled", text="Running...")
        CancelBtn.configure(state="normal")

        current_process = multiprocessing.Process(target=exec, args=(code,), daemon=True)

        current_process.start()
        root.after(500, check_process_finished)

    def cancel_execution():
        global current_process
        if current_process and current_process.is_alive():
            current_process.terminate()
            current_process = None

        ExecuteBtn.configure(state="normal", text="▶  Execute")
        CancelBtn.configure(state="disabled")

    def show_model_result(result):

        insert_to_CodeBox(f"{result["code"]}",History[-1]["ID"],True)

        print(result["risk"])
        print(result["request_name"])
        print(result["response"])
        print(result["icon"])

        insert_to_ChatBox(f"bot: {result["response"]}\n")
        RiskLabel.configure(text= f"Risk: {result["risk"]}")
        #print(History[-1]["ID"])
        history_button(HistoryBox, result["request_name"],History[-1]["ID"])


        status.configure(text="●  Status:  Running", text_color="#22c55e")
        send_btn.configure(state="normal")

    def show_model_error(error):
        print("Model error:", error)

        status.configure(text="●  Status:  Error", text_color="#ef4444")
        send_btn.configure(state="normal")

    def save_this():
        global Saved
        for item in History:
            if item["ID"] == CodeBox.history_id:
                spec = item
                try:
                    spec["ID"] = f"{int(Saved[-1]["ID"]) +1}"
                except:
                    print("firstsave?")
                    spec["ID"] = len(Saved)
                Saved.append(spec)
                update_saved()
                saved_button(SavedCommandsBox, spec["request_name"], spec["ID"], spec["icon"])

    def show_saved():
        for item in Saved:
            saved_button(SavedCommandsBox, item["request_name"],item["ID"],item["icon"])

    def clear_command_history():
        global History

        children = [
            child for child in HistoryBox.winfo_children()
            if isinstance(child, CTkButton)
        ]
        for child in children:
            child.destroy()




    root = CTk()
    root.geometry("1130x680")
    root.configure(fg_color="#080d18")  # main app background



    #FRAMES

    HeaderFrame = CTkFrame(
        root,
        fg_color="#090f1d",  # front panel color
        width=1200,
        height=50,
        border_width=1,
        corner_radius=0,
        border_color="#26324a",  # subtle border
    )
    HeaderFrame.place(y=0, x=0)

    CTkLabel(HeaderFrame,text="🤖 BOT HELPER",font= ('bold', 18,'bold')).place(x=10, y=10)

    SavedFrame = CTkFrame(root, fg_color="#0d1424", width=250, height=630, border_width=1, border_color="#26324a",
                          corner_radius=0)
    SavedFrame.place(y=50, x=0)

    CTkLabel(SavedFrame, text="SAVED COMMANDS", text_color="#94a3b8", font=("Segoe UI", 11, "bold")).place(x=18, y=18)

    SavedCommandsBox = CTkScrollableFrame(SavedFrame, fg_color="#0d1424", width=210, height=225, border_width=1,
                                          border_color="#1e293b", corner_radius=8)
    SavedCommandsBox.place(x=14, y=45)
    SavedCommandsBox._scrollbar.grid_remove()

    CTkLabel(SavedFrame, text="COMMAND HISTORY", text_color="#94a3b8", font=("Segoe UI", 11, "bold")).place(x=18, y=295)

    HistoryBox = CTkScrollableFrame(SavedFrame, fg_color="#0d1424", width=210, height=225, border_width=1,
                                    border_color="#1e293b", corner_radius=8)
    HistoryBox.place(x=14, y=322)
    HistoryBox._scrollbar.grid_remove()

    ClearHistoryBtn = CTkButton(
        SavedFrame,
        text="🗑  Clear History",
        width=205,
        height=38,
        fg_color="#2a1418",
        hover_color="#3f1d23",
        border_width=1,
        border_color="#7f1d1d",
        text_color="#fca5a5",
        font=("Segoe UI", 12, "bold"),
        corner_radius=7,
        command=clear_command_history
    )
    ClearHistoryBtn.place(x=20, y=575)



    #saved_button(SavedCommandsBox, "🌐  Open Google")


    #history_button(HistoryBox, "move mouse")



    RightBorder = CTkFrame(
        SavedFrame,
        width=2,
        height=230,
        #fg_color="#1e293b"
        fg_color = "#1e293b"
    )
    RightBorder.place(x=230, y=50)

    RightBorder = CTkFrame(
        SavedFrame,
        width=2,
        height=230,
        #fg_color="#1e293b"
        fg_color = "#1e293b"
    )

    RightBorder.place(x=230, y=328)

    #CONFIGFRAME
    ConfigFrame = CTkFrame(
        root,
        fg_color="#0d1424",  # front panel color
        width=860,
        height=70,
        border_width=1,
        border_color="#26324a",  # subtle border
        corner_radius=12
    )
    ConfigFrame.place(y=120, x=260)

    CTkLabel(ConfigFrame, text="Max Tokens", text_color="#94a3b8", font=("Segoe UI", 12, "bold")).place(x=28, y=2)
    maxTokensEntry = CTkEntry(ConfigFrame, width=190, height=36, fg_color="#0f172a", border_color="#26324a", border_width=1, corner_radius=8, text_color="#e5e7eb", font=("Segoe UI", 14))
    maxTokensEntry.place(x=28, y=24)
    maxTokensEntry.insert(0, "2000")

    CTkLabel(ConfigFrame, text="Temperature", text_color="#94a3b8", font=("Segoe UI", 12, "bold")).place(x=270, y=2)

    temperatureEntry = CTkEntry(ConfigFrame, width=190, height=36, fg_color="#0f172a", border_color="#26324a", border_width=1, corner_radius=8, text_color="#e5e7eb", font=("Segoe UI", 14))
    temperatureEntry.place(x=270, y=24)
    temperatureEntry.insert(0, "0.1")

    ResetBtn = CTkButton(ConfigFrame, text="Clear Chat", width=150, height=36, fg_color="#111827", hover_color="#1e1b4b", border_width=1, border_color="#26324a", text_color="#ddd6fe", font=("Segoe UI", 13, "bold"), command= clear_chat)
    ResetBtn.place(x=675, y=17)


    #CHATFRAME
    ChatFrame = CTkFrame(root,
        fg_color="#0d1424",  # front panel color
        width=425,
        height=390,
        border_width=1,
        border_color="#26324a",  # subtle border
        corner_radius=12
    )
    ChatFrame.place(y=200, x=260)

    ChatTitle = CTkLabel(
        ChatFrame,
        text="💬  Chat",
        text_color="#c084fc",
        font=("Segoe UI", 18, "bold")
    )
    ChatTitle.place(x=18, y=12)


    ChatBox = CTkTextbox(
        ChatFrame,
        width=400,
        height=335,
        fg_color="#0d1424",
        border_width=0,
        corner_radius=0,
        text_color="#e5e7eb",
        font=("Segoe UI", 15),
        wrap="word",
        scrollbar_button_color="#0d1424",
        scrollbar_button_hover_color="#0d1424"
    )
    ChatBox.place(y=50, x=10)
    ChatBox.tag_config("user", foreground="#c084fc")
    ChatBox.tag_config("bot", foreground="#4ade80")
    ChatBox.tag_config("success", foreground="#22c55e")
    ChatBox.tag_config("link", foreground="#60a5fa")
    ChatBox.tag_config("time", foreground="#94a3b8")
    ChatBox.configure(state="disabled")





    CodeFrame = CTkFrame(
        root,
        fg_color="#0d1424",  # front panel color
        width=425,
        height=390,
        border_width=1,
        border_color="#26324a",  # subtle border
        corner_radius=12
    )
    CodeFrame.place(y=200, x=695)

    CodeTitle = CTkLabel(
        CodeFrame,
        text="</>  Code",
        text_color="#c084fc",
        font=("Segoe UI", 18, "bold")
    )
    CodeTitle.place(x=18, y=12)

    CopyCodeBtn = CTkButton(CodeFrame, text="Copy", width=85, height=32, fg_color="#111827", hover_color="#1e1b4b",
                            border_width=1, border_color="#26324a", text_color="#ddd6fe", font=("Segoe UI", 12),
                            corner_radius=8,command=lambda: pyperclip.copy(CodeBox.get("1.0", "end-1c")))
    CopyCodeBtn.place(x=320,y=10)

    CodeBox = CTkTextbox(CodeFrame, width=400, height=230, fg_color="#0b1220", border_width=1, border_color="#26324a",
                         corner_radius=10, text_color="#e5e7eb", font=("Consolas", 12),
                         scrollbar_button_color="#1e293b", scrollbar_button_hover_color="#334155", wrap="none")
    CodeBox.place(x=10, y=50)
    CodeBox.tag_config("keyword", foreground="#c084fc")
    CodeBox.tag_config("string", foreground="#22c55e")
    CodeBox.tag_config("function", foreground="#60a5fa")
    CodeBox.tag_config("comment", foreground="#64748b")
    CodeBox.tag_config("builtin", foreground="#fb7185")
    CodeBox.tag_config("number", foreground="#facc15")

    ExecuteBtn = CTkButton(CodeFrame, text="▶  Execute", width=125, height=42, fg_color="#6d28d9",
                           hover_color="#7c3aed", text_color="white", font=("Segoe UI", 13, "bold"), corner_radius=8,command= execute_command)
    ExecuteBtn.place(x=10, y=292)

    SaveCodeBtn = CTkButton(CodeFrame, text="💾  Save", width=125, height=42, fg_color="#111827", hover_color="#1e1b4b",
                            border_width=1, border_color="#26324a", text_color="#e5e7eb", font=("Segoe UI", 13, "bold"),
                            corner_radius=8, command= save_this)
    SaveCodeBtn.place(x=147, y=292)

    CancelBtn = CTkButton(CodeFrame, text="✕  Cancel", width=125, height=42, fg_color="#2a1418", hover_color="#3f1d23",
                          border_width=1, border_color="#7f1d1d", text_color="#fca5a5", font=("Segoe UI", 13, "bold"),
                          corner_radius=8, command= cancel_execution)
    CancelBtn.place(x=284, y=292)
    CancelBtn.configure(state="disabled")

    WarningLabel = CTkLabel(
        CodeFrame,
        text="🛡  Code is generated by AI. Please review before executing.",
        text_color="#94a3b8",
        font=("Segoe UI", 11)
    )
    WarningLabel.place(x=14, y=345)

    RiskLabel = CTkLabel(
        CodeFrame,
        text="Risk: Low",
        text_color="#94a3b8",
        font=("Segoe UI", 11)
    )
    RiskLabel.place(x=330, y=345)


    inputFrame = CTkFrame(
        root,
        fg_color="#0d1424",  # front panel color
        width=860,
        height=70,
        border_width=1,
        border_color="#26324a",  # subtle border
        corner_radius=12
    )
    inputFrame.place(y=600, x=260)

    status = CTkLabel(
        root,
        text="●  Status:  Running",
        text_color="#22c55e",
        font=("Segoe UI", 17, "bold")
    )
    status.place(x=260, y=74)

    input_entry = CTkEntry(
        inputFrame,
        placeholder_text="Type your command here...",
        height=46,
        width=705,
        fg_color="#0f172a",
        border_color="#6d28d9",
        text_color='white',
        placeholder_text_color='grey',
        font=("Segoe UI", 15)
    )
    input_entry.place(x= 10,y=12)
    input_entry.bind("<Return>",lambda event: send())



    send_btn = CTkButton(
        inputFrame,
        text="➤  Send",
        width=130,
        height=46,
        fg_color="#6d28d9",
        hover_color="#7c3aed",
        text_color="white",
        font=("Segoe UI", 15, "bold"),
        command=lambda: send()
    )
    send_btn.place(x= 720,y=12)



    def get_ollama_models():
        try:
            output = subprocess.check_output(
                ["ollama", "list"],
                text=True
            )

            lines = output.strip().split("\n")[1:]

            models = []

            for line in lines:
                if line.strip():
                    model_name = line.split()[0]
                    models.append(model_name)

            return models
        except Exception as e:
            print(e)
            return ["qwen3:8b"]


    print(get_ollama_models())
    ModelMenu = CTkOptionMenu(
        root,
        width=330,
        height=44,
        fg_color="#0f172a",
        button_color="#0f172a",
        button_hover_color="#1e1b4b",
        dropdown_fg_color="#0f172a",
        dropdown_hover_color="#1e1b4b",
        text_color="#e5e7eb",
        dropdown_text_color="#e5e7eb",
        font=("Segoe UI", 14),
        dropdown_font=("Segoe UI", 13),
        corner_radius=6
    )

    ModelMenu.place(x=760, y=62)
    ModelMenu.configure(values= get_ollama_models())
    ModelMenu.set("qwen3:8b")

    show_saved()





    root.mainloop()

if __name__ == '__main__':
    main()
