#pragma once

#include "settings/settings_common.h"
#include "settings/settings_common_session.h"

namespace Settings {

class PluginManager final : public Section<PluginManager> {
public:
	PluginManager(QWidget *parent, not_null<Window::SessionController*> controller);
	[[nodiscard]] rpl::producer<QString> title() override;
};

} // namespace Settings
