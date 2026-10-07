/*
This file is part of Telegram Desktop,
the official desktop application for the Telegram messaging service.

For license and copyright information please follow this link:
https://github.com/telegramdesktop/tdesktop/blob/master/LEGAL
*/
#pragma once

#include "base/const_string.h"

#define TDESKTOP_REQUESTED_ALPHA_VERSION (0ULL)

#ifdef TDESKTOP_ALLOW_CLOSED_ALPHA
#define TDESKTOP_ALPHA_VERSION TDESKTOP_REQUESTED_ALPHA_VERSION
#else // TDESKTOP_ALLOW_CLOSED_ALPHA
#define TDESKTOP_ALPHA_VERSION (0ULL)
#endif // TDESKTOP_ALLOW_CLOSED_ALPHA

// used in Updater.cpp and Setup.iss for Windows
constexpr auto AppId = "{AB8971FC-807B-4A9C-B914-53D1B54461E8}"_cs;
constexpr auto AppNameOld = "netgram for Windows"_cs;
constexpr auto AppName = "netgram"_cs;
constexpr auto AppFile = "netgram"_cs;
constexpr auto AppVersion = 7002010;
constexpr auto AppVersionStr = "7.2.10";
// netgram dev releases use NetgramBuildId instead of Telegram's beta bit, so keep
// AppBetaVersion = false when upstream beta-version commits are merged.
constexpr auto AppBetaVersion = false;
constexpr auto AppAlphaVersion = TDESKTOP_ALPHA_VERSION;
