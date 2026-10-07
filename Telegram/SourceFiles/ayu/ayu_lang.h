// This is the source code of AyuGram for Desktop.
//
// We do not and cannot prevent the use of our code,
// but be respectful and credit the original author.
//
// Copyright @Radolyn, 2026
#pragma once

// netgram: built-in Russian translation of the strings that are absent
// from the official Telegram language pack (ayu_* and netgram lng_* keys).
// It is embedded in the resources and applied on top of the current
// language pack whenever the interface language is Russian.
class AyuLanguage final {
public:
	static void init();
	static void apply();

private:
	AyuLanguage();

	void load();
	void applyToCurrent() const;

	static AyuLanguage *instance;

	std::vector<std::pair<QByteArray, QByteArray>> _values;
	rpl::lifetime _lifetime;

};
