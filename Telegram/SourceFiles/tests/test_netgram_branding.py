#!/usr/bin/env python3
"""netgram branding: own name, own update channel, no links to other forks.

The client is a fork of Telegram Desktop with code from other forks merged
in. Their names may stay in internal identifiers and license headers, but
no link, channel or server of theirs may reach the interface or the network.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parent
RELEASES = "https://github.com/defl0r1an/netgram/releases"

# Scanned for forbidden links: everything that ends up in the binary,
# the package metadata or the published documentation.
SCAN = (
    "Telegram/SourceFiles",
    "Telegram/Resources/langs",
    "Telegram/Resources/winrc",
    "Telegram/Resources/qrc",
    "Telegram/build",
    "Telegram/cmake",
    "Telegram/CMakeLists.txt",
    "CMakeLists.txt",
    "lib/xdg",
    "snap",
    "docs",
    ".github",
    "README.md",
    "changelog.txt",
)
SKIP_DIRS = {"tests", "libs"}
TEXT_SUFFIXES = {
    ".cpp", ".h", ".mm", ".m", ".c", ".style", ".strings", ".rc", ".qrc",
    ".txt", ".cmake", ".md", ".yml", ".yaml", ".xml", ".desktop",
    ".service", ".iss", ".py", ".sh", ".bat", ".json", ".plist",
}
# Lower-case substrings: sites, channels, chats and servers of ZaStoGram
# and AyuGram, plus the old Forgejo home of the fork.
FORBIDDEN = (
    "zastogram",
    "git.zapret.moe",
    "zapretdiscordyoutube",
    "zapret-discordyoutube",
    "youtubediscord",
    "ayugram.one",
    "t.me/ayugram",
    "@ayugram",
    "ayugramreleases",
    "ayugramchat",
    "github.com/ayugram",
    "sentry.radolyn.com",
    "radolyn.com",
    "cdn.jsdelivr.net/gh/ayugram",
    "crowdin.com/project/ayugram",
    "ayugrambot",
    "exteragram.app",
    "t.me/ayusettings",
)


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *needles: str) -> None:
    text = source(path)
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise AssertionError(
            f"{path} lost netgram markers: {', '.join(missing)}")


def scanned_files():
    for entry in SCAN:
        path = REPO / entry
        if path.is_file():
            yield path
            continue
        if not path.is_dir():
            continue
        for file in path.rglob("*"):
            if not file.is_file() or file.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if SKIP_DIRS.intersection(file.relative_to(path).parts[:-1]):
                continue
            yield file


def check_forbidden() -> None:
    found = []
    for file in scanned_files():
        try:
            text = file.read_text(encoding="utf-8").lower()
        except UnicodeDecodeError:
            continue
        for needle in FORBIDDEN:
            if needle in text:
                found.append(f"{file.relative_to(REPO)}: {needle}")
    if found:
        raise AssertionError(
            "links of other forks are back:\n" + "\n".join(found))


def main() -> None:
    require(
        "SourceFiles/core/version.h",
        'constexpr auto AppName = "netgram"_cs;',
        'constexpr auto AppFile = "netgram"_cs;',
        "constexpr auto AppBetaVersion = false;",
    )
    require(
        "SourceFiles/core/launcher.cpp",
        'QApplication::setApplicationName(u"netgram"_q);',
        "netgram has two baked, independent channels",
        "cSetInstallBetaVersion(false);",
    )
    require(
        "SourceFiles/boxes/about_box.cpp",
        '#include "core/netgram_build.h"',
        "box->setTitle(AppName.utf16());",
        'u" (build %1)"_q.arg(NetgramBuildId.utf16())',
    )
    require(
        "SourceFiles/core/netgram_build.h",
        'constexpr auto NetgramBuildId = ""_cs;',
    )
    require(
        "SourceFiles/core/update_checker.cpp",
        '#include "core/netgram_build.h"',
        "kNetgramReleasesApi",
        "https://api.github.com/repos/defl0r1an/netgram/releases",
        "if (IsNetgramDevBuild())",
        "ResponseType::DevReleases",
        'release.value("prerelease").toBool()',
        "NetgramDevBuildNumber()",
        'name == "current4"',
        "_dev%2",
        "versionNum == AppVersion && !IsNetgramDevBuild()",
        "request.setTransferTimeout(int(kUpdateCheckTimeout));",
        "tryLoaders();",
    )
    updater = source("SourceFiles/core/update_checker.cpp")
    timeout = updater.split("void Updater::handleTimeout()", 1)[1].split(
        "bool Updater::tryLoaders()", 1
    )[0]
    if "cSetLastUpdateCheck(0)" in timeout or "_timer.callOnce" in timeout:
        raise AssertionError("a timed-out update check must not restart itself")

    application = source("SourceFiles/core/application.cpp")
    if RELEASES not in application:
        raise AssertionError("the netgram release history URL is missing")
    require(
        "SourceFiles/window/window_main_menu.cpp",
        "AppName.utf16()",
        "https://github.com/defl0r1an/netgram",
    )
    require(
        "SourceFiles/settings/sections/settings_advanced.cpp",
        "BuildUpdateSection(builder, true);",
        "return !downloading;",
        "Core::UpdateChecker checker;",
        "tr::lng_settings_check_now()",
    )
    advanced = source("SourceFiles/settings/sections/settings_advanced.cpp")
    if "lng_settings_install_beta" in advanced:
        raise AssertionError("the obsolete upstream beta switch returned")

    # GitHub serves the newest release assets at <repo>/releases/latest/download.
    localstorage = source("SourceFiles/storage/localstorage.cpp")
    if RELEASES + "/latest/download" not in localstorage:
        raise AssertionError("the GitHub latest-asset prefix is missing")
    if RELEASES + "/download/latest" in localstorage:
        raise AssertionError("the Forgejo latest-asset path order returned")

    require(
        "Resources/winrc/Telegram.rc",
        'VALUE "FileDescription", "netgram"',
        'VALUE "ProductName", "netgram"',
    )
    require(
        "SourceFiles/platform/linux/specific_linux.cpp",
        'u"io.github.defl0r1an.netgram"_q',
        'u":/misc/io.github.defl0r1an.netgram.desktop"_q',
    )
    require(
        "SourceFiles/platform/win/windows_toast_activator.h",
        'DECLSPEC_UUID("9BFCABA3-3818-4D79-94DF-1F38E535DD97")',
    )
    for name in ("desktop", "metainfo.xml", "service"):
        if not (REPO / "lib" / "xdg" / f"io.github.defl0r1an.netgram.{name}").is_file():
            raise AssertionError(f"lib/xdg lost the netgram .{name} file")
    require(
        "../.github/workflows/source-guards.yml",
        "release_guards.txt",
        "Run canonical release source guards",
    )
    if (ROOT / "SourceFiles" / "data" / "components" / "promo_suggestions.cpp").read_text(
            encoding="utf-8").lower().count("zastogram"):
        raise AssertionError("the pinned channel of another fork returned")
    check_forbidden()


if __name__ == "__main__":
    main()
