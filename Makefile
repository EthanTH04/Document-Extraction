.PHONY: paper clean-paper

paper:
	cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error paper.tex

clean-paper:
	cd paper && latexmk -C paper.tex
