# Sample assets

This directory can hold optional sample images or PDFs for manual experiments. The automated
tests dynamically generate their own images and multi-page PDFs so no binary fixtures are
committed to the repository. If you want to try the pipeline manually, drop files here, for
example:

- `sample_image.png`: a simple RGB image containing text.
- `sample_multipage.pdf`: a short PDF with at least two pages for PDF loading checks.

These files are intentionally excluded from version control to keep the repository free of
binary blobs.
