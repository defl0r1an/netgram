// This is the source code of AyuGram for Desktop.
//
// We do not and cannot prevent the use of our code,
// but be respectful and credit the original author.
//
// Copyright @Radolyn, 2026
#include "ayu/ayu_lang.h"

#include "lang/lang_file_parser.h"
#include "lang/lang_instance.h"

#include <QFile>

namespace {

// Embedded through Resources/qrc/telegram/telegram.qrc.
constexpr auto kRussianStringsPath = ":/misc/langs/netgram_ru.strings";

[[nodiscard]] bool IsRussianId(const QString &id) {
	return (id == u"ru"_q) || id.startsWith(u"ru-"_q);
}

[[nodiscard]] bool IsRussianLanguage(const Lang::Instance &lang) {
	return !lang.isCustom()
		&& (IsRussianId(lang.id()) || IsRussianId(lang.baseId()));
}

} // namespace

AyuLanguage *AyuLanguage::instance = nullptr;

AyuLanguage::AyuLanguage() = default;

void AyuLanguage::init() {
	if (instance) {
		instance->applyToCurrent();
		return;
	}
	// Intentionally never destroyed, lives for the whole app run.
	instance = new AyuLanguage;
	instance->load();

	auto &lang = Lang::GetInstance();

	// The language pack was switched (and its values were reset): put the
	// built-in strings back if the new language is Russian. When switching
	// to any other language the reset already removed them.
	lang.idChanges(
	) | rpl::on_next([=](const QString &) {
		instance->applyToCurrent();
	}, instance->_lifetime);

	// The cloud pack difference was applied, reapply ours on top, so that
	// nothing coming from the server can overwrite them.
	lang.updated(
	) | rpl::on_next([=] {
		instance->applyToCurrent();
	}, instance->_lifetime);

	// The cached pack was loaded at startup before we subscribed.
	instance->applyToCurrent();
}

void AyuLanguage::apply() {
	if (instance) {
		instance->applyToCurrent();
	}
}

void AyuLanguage::load() {
	QFile file(QString::fromLatin1(kRussianStringsPath));
	if (!file.open(QIODevice::ReadOnly)) {
		LOG(("netgram Lang Error: could not open built-in translation."));
		return;
	}
	const auto content = file.readAll();
	file.close();

	auto values = std::vector<std::pair<QByteArray, QByteArray>>();
	const Lang::FileParser parser(content, [&](
			QLatin1String key,
			const QByteArray &value) {
		values.emplace_back(QByteArray(key.data(), key.size()), value);
	});
	if (!parser.errors().isEmpty()) {
		LOG(("netgram Lang Error: %1").arg(parser.errors()));
	}
	_values = std::move(values);
}

void AyuLanguage::applyToCurrent() const {
	if (_values.empty()) {
		return;
	}
	auto &lang = Lang::GetInstance();
	if (!IsRussianLanguage(lang)) {
		return;
	}
	for (const auto &[key, value] : _values) {
		lang.resetValue(key);
		lang.applyValue(key, value);
	}
	lang.updatePluralRules();
}
