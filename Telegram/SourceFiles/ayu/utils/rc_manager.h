// This is the source code of AyuGram for Desktop.
//
// We do not and cannot prevent the use of our code,
// but be respectful and credit the original author.
//
// Copyright @Radolyn, 2026
#pragma once

#include "ayu/data/entities.h"

#include <QtNetwork/QNetworkReply>

extern std::unordered_set<ID> default_developers;
extern std::unordered_set<ID> default_channels;

struct CustomBadge
{
	EmojiStatusId emojiStatusId;
	QString text;
};

// netgram: the remote config (developer and supporter badges) is never
// requested and all the lists are empty, so no third-party people or
// channels get a badge. The manager only keeps its interface.
class RCManager final : public QObject
{
	Q_OBJECT
public:
	static RCManager &getInstance() {
		static RCManager instance;
		return instance;
	}

	RCManager(const RCManager &) = delete;
	RCManager &operator=(const RCManager &) = delete;
	RCManager(RCManager &&) = delete;
	RCManager &operator=(RCManager &&) = delete;

	void start();

	[[nodiscard]] const std::unordered_set<ID> &developers() const {
		return default_developers;
	}

	[[nodiscard]] const std::unordered_set<ID> &channels() const {
		return default_channels;
	}

	[[nodiscard]] const std::unordered_set<ID> &supporters() const {
		return _supporters;
	}

	[[nodiscard]] const std::unordered_set<ID> &supporterChannels() const {
		return _supporterChannels;
	}

	[[nodiscard]] const std::unordered_map<ID, CustomBadge> &supporterCustomBadges() const {
		return _customBadges;
	}

private:
	RCManager() = default;
	~RCManager() = default;

	std::unordered_set<ID> _supporters = {};
	std::unordered_set<ID> _supporterChannels = {};
	std::unordered_map<ID, CustomBadge> _customBadges = {};

};
