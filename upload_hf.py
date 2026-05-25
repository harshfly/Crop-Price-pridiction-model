import os
import sys

# Attempt to install if missing (when run in container)
try:
    from huggingface_hub import HfApi
except ImportError:
    os.system('pip install huggingface_hub')
    from huggingface_hub import HfApi

print('Uploading to Hugging Face Spaces...')
api = HfApi()
try:
    api.upload_folder(
        folder_path='.',
        repo_id='haarsh0910/krishimitra-ai',
        repo_type='space',
        token=os.environ.get('HF_TOKEN'),
        ignore_patterns=[
            '.git/*', 'venv/*', 'venv_broken/*', 
            'node_modules/*', 'saas-frontend/node_modules/*', 
            '__pycache__/*', 'data/raw/*',
            'upload_hf.py'
        ]
    )
    print('Upload complete!')
except Exception as e:
    print('Error:', str(e))
    sys.exit(1)
