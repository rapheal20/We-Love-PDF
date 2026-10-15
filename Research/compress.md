## PDF Compressing

PDFs are mainly heavy bcz of the following:
1. Uncompressed images
2. Redundant Streams of data - duplicate fonts, uncompressed text/vectors, leftover metadata
3. Unnecessary Objects -  deleted pages and edit histories


# Working Of The Compressor

1. Images of the PDF:
    - scan the pdf to find embedded image streams
    - pass those extracted streams through pillow
        - lower the quality
        - downscale the resolution if very massive
    - swap the old image streams with the new ones

2. Duplicate Resources:
    - scan the PDF, find resources like fonts, colour spaces, images
    - parse throught the pdf and find if the same fonts are repeated then remove
    - fix the references

3. Remove garbage
    - check the pdf for the leftover after pages or elements were deleted
    - find them and delete them

- Largest effect is from the images
