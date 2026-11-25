#pragma once

#include "settings/settings_common.h"
#include "settings/settings_common_session.h"

namespace Ui { class VerticalLayout; }

namespace Settings {

void FillPluginManagerEngine(
	not_null<Ui::VerticalLayout*> container,
	not_null<Window::SessionController*> controller);

class PluginManager final : public Section<PluginManager> {
public:
	PluginManager(QWidget *parent, not_null<Window::SessionController*> controller);
	[[nodiscard]] rpl::producer<QString> title() override;
};

} // namespace Settings
