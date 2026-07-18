import uvicorn


def main() -> None:
    uvicorn.run("rosens.api:app", host="0.0.0.0", port=8000)  # noqa: S104


if __name__ == "__main__":
    main()
