#!/bin/bash

POSITIONAL=()
while [[ $# -gt 0 ]]
do
	key="$1"

	case ${key} in
		-fl|--flatpak-local)
			FLATPAK_LOCAL=1
			shift # past argument
			;;
		-fr|--flatpak-remote)
			FLATPAK_REMOTE=1
			shift # past argument
			;;
		-fi|--flatpak-install)
			FLATPAK_INSTALL=1
			shift # past argument
			;;
		-fb|--flatpak-bundle)
			FLATPAK_BUNDLE=1
			shift # past argument
			;;
		*)    # unknown option
			POSITIONAL+=("$1") # save it in an array for later
			shift # past argument
			;;
	esac
done
set -- "${POSITIONAL[@]}" # restore positional parameters

APP_ID="com.leinardi.gwe"
BUILD_DIR="build"
OUTPUT_DIR="${BUILD_DIR}/output"
MESON_BUILD_DIR="${BUILD_DIR}/meson"
FLATPAK_BUILD_DIR="${BUILD_DIR}/flatpak/build"
FLATPAK_REPO_DIR="${BUILD_DIR}/flatpak/repo"
FLATPAK_INSTALL_PARAMETERS="--user --install"
FLATPAK_REMOTE_MANIFEST="flatpak/${APP_ID}.json"
FLATPAK_LOCAL_MANIFEST="build/flatpak/${APP_ID}.json"
FLATPAK_OUTPUT_FILE="${OUTPUT_DIR}/${APP_ID}.flatpak"
INSTALL_DIR="${OUTPUT_DIR}/install"

function build_flatpak {
	mkdir -p ${FLATPAK_REPO_DIR} && \
	mkdir -p ${FLATPAK_BUILD_DIR} && \

	time flatpak-builder --force-clean $2 --install-deps-from=flathub --repo=${FLATPAK_REPO_DIR} ${FLATPAK_BUILD_DIR} $1 && \
	desktop-file-validate build/flatpak/build/files/share/applications/com.leinardi.gwe.desktop || exit $?
}

function build_flatpak_bundle {
	mkdir -p ${OUTPUT_DIR} && \
	time flatpak build-bundle ${FLATPAK_REPO_DIR} ${FLATPAK_OUTPUT_FILE} ${APP_ID} || exit $?
}

if [[ ${#POSITIONAL[@]} -ne 0 ]]; then
	echo "Unknown option ${POSITIONAL}"
	exit 1
fi

appstream-util validate-relax data/com.leinardi.gwe.appdata.xml || exit $?
appstream-util appdata-to-news data/com.leinardi.gwe.appdata.xml | sed '/^~*$/s/~/=/g' > CHANGELOG.md
[[ -d ${OUTPUT_DIR} ]] && rm -rfv ${OUTPUT_DIR}
find . -regex '^.*\(__pycache__\|\.py[co]\)$' -delete

if [[ ${FLATPAK_REMOTE} -eq 1 ]]; then
	if [[ ${FLATPAK_INSTALL} -eq 1 ]]; then
		build_flatpak "${FLATPAK_REMOTE_MANIFEST}" "${FLATPAK_INSTALL_PARAMETERS}"
	else
		build_flatpak ${FLATPAK_REMOTE_MANIFEST}
	fi
	if [[ ${FLATPAK_BUNDLE} -eq 1 ]]; then
		build_flatpak_bundle
	fi
elif [[ ${FLATPAK_LOCAL} -eq 1 ]]; then
	scripts/make_local_manifest.py ${FLATPAK_REMOTE_MANIFEST} ${FLATPAK_LOCAL_MANIFEST}
	if [[ ${FLATPAK_INSTALL} -eq 1 ]]; then
		build_flatpak "${FLATPAK_LOCAL_MANIFEST}" "${FLATPAK_INSTALL_PARAMETERS}"
	else
		build_flatpak ${FLATPAK_LOCAL_MANIFEST}
	fi
	if [[ ${FLATPAK_BUNDLE} -eq 1 ]]; then
		build_flatpak_bundle
	fi
elif [[ ${FLATPAK_BUNDLE} -eq 1 ]]; then
	build_flatpak_bundle
else
	[[ -d ${MESON_BUILD_DIR} ]] && rm -rfv ${MESON_BUILD_DIR}
	mkdir -pv ${MESON_BUILD_DIR} ${INSTALL_DIR} && \
	meson . ${MESON_BUILD_DIR} --prefix=$PWD/${INSTALL_DIR} && \
	ninja -v -C ${MESON_BUILD_DIR} && \
	desktop-file-validate build/meson/data/com.leinardi.gwe.desktop && \
	ninja -v -C ${MESON_BUILD_DIR} install
fi
