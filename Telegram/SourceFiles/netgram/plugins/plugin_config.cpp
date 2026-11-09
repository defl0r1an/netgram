#include "netgram/plugins/plugin_config.h"

#include <QtCore/QJsonDocument>
#include <QtCore/QFile>
#include <QtCore/QSaveFile>

namespace Netgram {
namespace {

constexpr auto kSaveDelay = crl::time(1000);

[[nodiscard]] const QJsonObject &Defaults() {
	static const auto result = QJsonObject{
		{ u"plugins_guard"_q, 0 },
		{ u"guard_llm_provider"_q, 0 },
		{ u"guard_llm_key"_q, QString() },
		{ u"guard_llm_model"_q, QString() },
		{ u"port_llm_provider"_q, 0 },
		{ u"port_llm_key"_q, QString() },
		{ u"port_llm_model"_q, QString() },
		{ u"port_llm_endpoint"_q, QString() },
		{ u"port_llm_mode"_q, 0 },
		{ u"guard_model_check"_q, 0 },
		{ u"guard_model_version"_q, QString() },
		{ u"plugins_guard_blocked"_q, QString() },
		{ u"plugins_no_auto_safe"_q, false },
		{ u"plugins_enabled"_q, true },
		{ u"plugins_pinned"_q, QString() },
		{ u"plugins_developer_mode"_q, false },
		{ u"plugins_compact_view"_q, false },
		{ u"plugins_unknown_sources"_q, false },
		{ u"plugins_safe_mode"_q, false },
	};
	return result;
}

} // namespace

Config &Config::Instance() {
	static const auto result = new Config();
	return *result;
}

Config::Config()
: _saveTimer([=] { saveNow(); }) {
}

void Config::setWorkingDir(const QString &path) {
	_path = path + u"tdata/plugin_preferences.json"_q;
	_loaded = false;
	_values = QJsonObject();
	load();
}

QString Config::path() const {
	return _path;
}

void Config::load() {
	if (_loaded) {
		return;
	}
	if (_path.isEmpty()) {
		return;
	}
	_loaded = true;
	auto file = QFile(path());
	if (!file.open(QIODevice::ReadOnly)) {
		return;
	}
	const auto document = QJsonDocument::fromJson(file.readAll());
	if (document.isObject()) {
		_values = document.object();
	}
}

QJsonValue Config::value(const QString &key) const {
	const_cast<Config*>(this)->load();
	const auto i = _values.constFind(key);
	if (i != _values.constEnd()) {
		return *i;
	}
	return Defaults().value(key);
}

void Config::set(const QString &key, QJsonValue value) {
	load();
	if (value == Defaults().value(key)) {
		if (!_values.contains(key)) {
			return;
		}
		_values.remove(key);
	} else if (_values.value(key) == value) {
		return;
	} else {
		_values.insert(key, value);
	}
	_saveTimer.callOnce(kSaveDelay);
	_changes.fire_copy(key);
}

bool Config::boolValue(const QString &key) const {
	return value(key).toBool();
}

int Config::intValue(const QString &key) const {
	return value(key).toInt();
}

QString Config::stringValue(const QString &key) const {
	return value(key).toString();
}

void Config::setBool(const QString &key, bool value) {
	set(key, value);
}

void Config::setInt(const QString &key, int value) {
	set(key, value);
}

void Config::setString(const QString &key, const QString &value) {
	set(key, value);
}

rpl::producer<bool> Config::boolChanges(const QString &key) const {
	return rpl::single(
		boolValue(key)
	) | rpl::then(_changes.events(
	) | rpl::filter(
		rpl::mappers::_1 == key
	) | rpl::map([=] {
		return boolValue(key);
	})) | rpl::distinct_until_changed();
}

rpl::producer<QString> Config::stringChanges(const QString &key) const {
	return rpl::single(
		stringValue(key)
	) | rpl::then(_changes.events(
	) | rpl::filter(
		rpl::mappers::_1 == key
	) | rpl::map([=] {
		return stringValue(key);
	})) | rpl::distinct_until_changed();
}

rpl::producer<int> Config::intChanges(const QString &key) const {
	return rpl::single(
		intValue(key)
	) | rpl::then(_changes.events(
	) | rpl::filter(
		rpl::mappers::_1 == key
	) | rpl::map([=] {
		return intValue(key);
	})) | rpl::distinct_until_changed();
}

rpl::producer<QString> Config::changes() const {
	return _changes.events();
}

QByteArray Config::exportJson() const {
	const_cast<Config*>(this)->load();
	return QJsonDocument(_values).toJson(QJsonDocument::Indented);
}

bool Config::importJson(const QByteArray &data) {
	const auto document = QJsonDocument::fromJson(data);
	if (!document.isObject()) {
		return false;
	}
	load();
	const auto imported = document.object();
	for (auto i = imported.begin(); i != imported.end(); ++i) {
		if (Defaults().contains(i.key())) {
			set(i.key(), i.value());
		}
	}
	return true;
}

void Config::reset() {
	load();
	const auto keys = _values.keys();
	for (const auto &key : keys) {
		set(key, Defaults().value(key));
	}
}

void Config::saveNow() {
	_saveTimer.cancel();
	if (_path.isEmpty()) {
		return;
	}
	auto file = QSaveFile(path());
	if (!file.open(QIODevice::WriteOnly)) {
		return;
	}
	file.write(QJsonDocument(_values).toJson(QJsonDocument::Indented));
	file.commit();
}

bool IsBoolKey(const QString &key) {
	return Defaults().value(key).isBool();
}

bool Bool(const QString &key) {
	return Config::Instance().boolValue(key);
}

int Int(const QString &key) {
	return Config::Instance().intValue(key);
}

QString String(const QString &key) {
	return Config::Instance().stringValue(key);
}

} // namespace Netgram
