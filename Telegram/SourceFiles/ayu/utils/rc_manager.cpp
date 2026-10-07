// This is the source code of AyuGram for Desktop.
//
// We do not and cannot prevent the use of our code,
// but be respectful and credit the original author.
//
// Copyright @Radolyn, 2026
#include "ayu/utils/rc_manager.h"

// netgram: no built-in developer or official channel lists either.
std::unordered_set<ID> default_developers = {};

std::unordered_set<ID> default_channels = {};

void RCManager::start() {
	// netgram: no requests to remote config servers.
	DEBUG_LOG(("RCManager: remote config is disabled"));
}
