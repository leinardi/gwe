# Releasing

1. `flatpak run org.freedesktop.appstream-glib validate data/com.leinardi.gwe.appdata.xml`
2. Bump the `APP_VERSION` property in `gwe/conf.py` based on Major.Minor.Patch naming scheme
3. Update `data/com.leinardi.gwe.appdata.xml` for the impending release.
4. Update the `README.md` with the new changes (if necessary).
5. `git commit -am "Prepare for release X.Y.Z"` (where X.Y.Z is the version you set in step 1)
6. `flatpak uninstall com.leinardi.gwe --assumeyes; ./build.sh --flatpak-local --flatpak-install --flatpak-bundle && flatpak run com.leinardi.gwe --debug`
7. Tag version `X.Y.Z` (`git tag -s X.Y.Z`) (where X.Y.Z is the version you set in step 1)
8. Update tag and SHA in `flatpak/com.leinardi.gwe.json`
9. `git push --follow-tags` 
10. Trigger Flathub build bot `cd flatpak && git commit -am "Release X.Y.Z" && git push` (where X.Y.Z is the version you set in step 1)
11. Make a PR to the Flathub repository master, test the build and, if OK, merge the PR
12. `git commit -am "Release X.X.X" && git push` (where X.Y.Z is the version you set in step 1)
13. Create a PR from [master](../../tree/master) to [release](../../tree/release)
