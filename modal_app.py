import modal

app = modal.App("biaslens-backend")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi>=0.104.0",
        "pydantic>=2.0",
        "pydantic-settings>=2.0",
        "pandas>=2.1.0",
        "numpy>=1.26.0",
        "scikit-learn>=1.3.0",
        "xgboost>=2.0.0",
        "shap>=0.43.0",
        "joblib>=1.3.0",
        "requests>=2.31.0",
        "python-multipart>=0.0.6",
        "python-dotenv>=1.0.0",
    )
    .add_local_dir("backend", remote_path="/root/backend", copy=True)
    .add_local_dir("shared", remote_path="/root/shared", copy=True)
)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("biaslens-secrets")],
    cpu=4.0,
    memory=8192,
    timeout=300,
    scaledown_window=120,
)
@modal.concurrent(max_inputs=10)
@modal.asgi_app()
def serve():
    import sys

    sys.path.insert(0, "/root")
    from backend.main import app as fastapi_app

    return fastapi_app
