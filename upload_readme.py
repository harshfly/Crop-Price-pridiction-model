from huggingface_hub import HfApi

api = HfApi()
try:
    print('Uploading README.md...')
    api.upload_file(
        path_or_fileobj='/app/README.md',
        path_in_repo='README.md',
        repo_id='haarsh0910/krishimitra-ai',
        repo_type='space',
        token='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',
    )
    print('Upload complete!')
except Exception as e:
    print('Error:', str(e))
