## paper-llama

paper-llama integrates your private paperless-ngx and ollama instance. It periodically checks for new documents, takes the OCR text and sends it to LLM model for analysis. Depending on prompt, the LLM returns title, date, corespondents, tags and document type. The document is then updated by returned information.

There are similar projects out there, but I find them too bloated. This program is much simpler, but at least gives you full control over prompting.

## Testing

While you can use docker for running it against new documents, you should start with the following test to design the prompt.

1. Clone the project, create a virtual environment and install dependencies:
```
git clone git@github.com:Tomasinjo/paper-llama.git
cd paper-llama
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

<br>

2. Edit .env and modify access data for paperless-ngx and ollama:
```
PAPERLESS_URL=http://paperless_app:8000
PAPERLESS_TOKEN=0xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxab68

OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=gemma3:27b-32k
```

<br>

3. Check it works. Go to your paperless-ngx and open any document. In URL, there is document ID. Add it to `--doc-id` flag. The flag `--dry-run` will not modify documents on your paperless-ngx, but only log LLM response:
```
(venv) tom @ server ~/apps/paperless/paper-llama $ python3 main.py --mode manual --doc-id 127 --dry-run
2025-12-23 21:13:57,827 - PaperlessAI - INFO - Loaded metadata: 152 tags, 78 correspondents.
2025-12-23 21:13:57,827 - PaperlessAI - INFO - Found the following variables to replace in prompt: ['%TYPES%']
2025-12-23 21:14:01,013 - PaperlessAI - INFO - Processing Document 127: 'scan_001'
2025-12-23 21:14:05,309 - PaperlessAI - INFO - Received response from Ollama
2025-12-23 21:14:05,309 - PaperlessAI - INFO - LLM Suggestions: {"title":"Splošna privolitev in pogodbeni pogoji","created":"2024-04-04","correspondent":"RandomCorp","document_type":"contract","tags":["Privolitev","Tom Kern","Name Surname"]}
2025-12-23 21:14:05,309 - PaperlessAI - INFO - Not updating document due to dry run
```
If you don't get any connection errors, you can proceed, else fix the URLs.

<br>

4. Read section [About prompt](#About-prompt) below, modify the file `prompt.txt` and run with `--dry-run` until you are satisfied with the result. You can also remove `--dry-run` to see if document in paperless-ngx is updated correctly.

Proceed by scheduling it to run periodically. You can run it as script on host using flags `--mode auto`, or even better, [with docker compose](##Deploying-in-docker).


## About prompt

Prompt is expected in file `prompt.txt`. The OCR content is appended at the end before it is send to LLM. 

Feel free to modify the prompt, but please note that paper-llama expects JSON response:
```
{
    "title": string,
    "created": string, YYYY-MM-DD,
    "correspondent": string,
    "document_type": string,
    "tags": array
}
```
It is OK if you decide to remove some keys, or if LLM responds with `null` value - it will simply be ignored from document update.

You can use variables which are replaced by actual values from paperless-ngx. Possible variables:

- `%CORRESPONDENTS%`  -> replaced by array of correspondents defined in paperless-ngx. Paperless supports only one correspondent per document, prompt accordingly. If LLM outputs a value that does exist yet, it will be created.
- `%TYPES%`  -> replaced by array of document types defined in paperless-ngx. Paperless supports only one document type per document, prompt accordingly. If LLM outputs a value that does exist yet, it will be created.
- `%TAGS%`  -> replaced by array of tags defined in paperless-ngx. There can be multiple tags per document. Tell LLM that it should return array. If LLM outputs a value that does exist yet, it will be created.

You can find my prompt in [prompt.txt](prompt.txt).


## Models

You can use any model supported by ollama and of course your hardware. Model gemma3:27b works great for me and consumes around 19GB of memory.

[Don't forget to extend context token limit in ollama when deploying the model. By default it is only 2048, which is too low for larger documents](https://docs.ollama.com/faq#how-can-i-specify-the-context-window-size)

## Deploying in docker

After you fine-tuned your prompt, you can deploy it in docker where paper-llama will run periodically.

1. Put files `docker-compose.yml`, `prompt.txt` and `.env` in a new directory.
2. Modify `.env`:
    - `OVERRIDE_EXISTING_TAGS=True`  --> controls if existing tags can be replaced with those provided by LLM. If set to False, the LLM tags will be added alongside the existing tags in paperless-ngx.
    - `SCAN_INTERVAL=600`  --> How often to check for new documents in seconds
3. Deploy it: `docker-compose up -d`
4. Check the logs: `docker compose logs -fn 50`


## Preventing duplicated processing

The paper-llama relies on paperless-ngx to track already processed documents, specifically a custom field "AI Processed" of type boolean. It is created automatically in paperless-ngx the first time the paper-llama is ran without `--dry-run` flag.

When document is modified by paper-llama, it will set this custom field to True for subject document. Until it is set like that, it will be skipped from future processing (only applicable to `--mode auto`). You can remove it anytime to reprocess the document.
