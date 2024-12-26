## process-intake-form

## Grab bag

Copy all images in the Pictures folder from the last 15 minutes.
```
find ~/Pictures -type f -mmin -15 -exec cp {} images \;
```

Rotate all images in the images folder 90 degrees to the left (without entering any additional directories).
```
find images -maxdepth 1 -type f | xargs -I {} magick {} -rotate -90 {}
```
