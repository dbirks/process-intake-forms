## process-intake-forms

## Grab bag

Copy all images in the Pictures folder from the last 15 minutes.
```
find ~/Pictures -type f -mmin -15 -exec cp {} inputs/images \;
```

Rotate all images in the images folder 90 degrees to the left (without entering any additional directories).
```
find inputs/images -maxdepth 1 -type f | xargs -I {} magick {} -rotate -90 {}
```

## todo

- [ ] list species instead of whole csv
- [ ] indiana counties only
- [ ] ids must be between 0000 and 2000
- [ ] don't sort
