# Scrape + DeepSeek Workflow Project

## Structure

```text
scrape_deepseek_project/
  main.py
  scrapling_modules/
    sulwhasoo_scrapling_module.py
    thesaemcosmetic_scrapling_module.py
  deepseek_module.py
  deepseek_prompt.md
  requirements.txt
  tests/
    test_all.py
    test_sulwhasoo_scrapling_module.py
    test_thesaemcosmetic_scrapling_module.py
    test_deepseek_module.py
```

## Install

```powershell
pip install -r requirements.txt
```

## Run Workflow

```powershell
python main.py --url "https://example.com" --api-key "YOUR_DEEPSEEK_API_KEY"
```

Optional environment variables:

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`

## Test

Run unified test entry:

```powershell
python tests/test_all.py
```

Alternative:

```powershell
python -m unittest discover -s tests -v
```
