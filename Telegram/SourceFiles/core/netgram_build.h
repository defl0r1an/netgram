/*
This file is part of Telegram Desktop,
the official desktop application for the Telegram messaging service.

For license and copyright information see the local LEGAL file.
*/
#pragma once

#include "base/const_string.h"

// netgram build identity, shown in the About box.
//
// An empty id means a regular build that takes stable updates.
// "dev-<number>" makes a dev build: it is offered GitHub pre-releases of
// defl0r1an/netgram tagged "dev-<number>" with a bigger number, even with
// the same AppVersion. Nothing rewrites this line yet: .github/workflows/win.yml
// builds with an empty id, so the dev channel stays unused until a release
// script or CI step starts setting it (e.g. "dev-${{ github.run_number }}").
//
// Keep the line below on one line and keep this header trivial to include:
// only boxes/about_box.cpp and core/update_checker.cpp do, so a new build id
// costs two translation units instead of a full rebuild.
constexpr auto NetgramBuildId = ""_cs;
