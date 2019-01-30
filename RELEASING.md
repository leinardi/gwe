# Releasing

1. Bump the `APP_VERSION` property in `gwe/conf.py` based on Major.Minor.Patch naming scheme
2. Update `data/com.leinardi.gwe.appdata.xml` for the impending release.
3. Update the `README.md` with the new changes (if necessary).
4. `./build.sh --flatpak-local --flatpak-install --flatpak-bundle && flatpak run com.leinardi.gwe` 
5. `git commit -am "Prepare for release X.Y.Z" && git push` (where X.Y.Z is the version you set in step 1)
6. Tag version `X.Y.Z` (`git tag -s X.Y.Z && git push --tags`)
7. Update tag and SHA in `flatpak/com.leinardi.gwe.json`
8. Trigger Flathub build bot `cd flatpak && git commit -am "Release X.Y.Z" && git push` (where X.Y.Z is the version you set in step 1)
10. Test the build and, if OK, make a PR to the Flathub repository master
11. Create a PR from [master](../../tree/master) to [release](../../tree/release)
