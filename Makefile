.PHONY: all clean-outputs install

all:
	python run_pipeline.py

install:
	pip install -r requirements.txt --break-system-packages

clean-outputs:
	rm -rf data/processed/* figures/*
	@echo "Cleared previous outputs — run 'make all' to regenerate."
