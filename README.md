## process-intake-forms

### Notes

Copy all images in the Pictures folder from the last 30 minutes.
```
find ~/Pictures -type f -mmin -30 -exec cp {} inputs/images \;
```

Rotate all images in the images folder 90 degrees to the left (without entering any additional directories).
```
find inputs/images -maxdepth 1 -type f | xargs -I {} magick {} -rotate -90 {}
```

Set up dotenv file, add openai key, and run:
```
cp .env.example .env
uv run main.py
```

### To-do

- [x] write progress to csv instead of keeping a dataframe in memory, in case of any weird error that causes exit
- [x] parallelize so it doesn't take most of an hour to complete
