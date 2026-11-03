#include "netgram/plugins/plugin_manager.h"

#include "netgram/plugins/plugin_config.h"
#include "netgram/plugins/plugins.h"
#include "netgram/plugins/plugins_ui.h"
#include "ayu/ui/settings/settings_main.h"
#include "ayu/ui/settings/settings_ayu_utils.h"
#include "core/application.h"
#include "core/file_utilities.h"
#include "lang_auto.h"
#include "settings/settings_builder.h"
#include "styles/style_menu_icons.h"
#include "styles/style_settings.h"
#include "ui/widgets/buttons.h"
#include "ui/wrap/vertical_layout.h"
#include "window/window_session_controller.h"

namespace Settings {
namespace {

using namespace Builder;

const auto kMeta = BuildHelper({
	.id = PluginManager::Id(),
	.parentId = AyuMain::Id(),
	.title = &tr::lng_netgram_plugins_manager_title,
	.icon = &st::menuIconBotCommands,
}, [](SectionBuilder &builder) {
	const auto controller = builder.controller();
	const auto toggle = [&](const QString &key, rpl::producer<QString> label) {
		return builder.addButton({
			.id = u"netgram/"_q + key,
			.title = std::move(label),
			.st = &st::settingsButtonNoIcon,
			.toggled = Netgram::Config::Instance().boolChanges(key),
		});
	};
	builder.addSkip();
	const auto enabled = toggle(u"plugins_enabled"_q, tr::lng_netgram_plugins_manager_enabled());
	enabled->toggledChanges() | rpl::filter([](bool value) {
		return value != Netgram::Bool(u"plugins_enabled"_q);
	}) | rpl::on_next([=](bool value) {
		Netgram::Config::Instance().setBool(u"plugins_enabled"_q, value);
		Netgram::Config::Instance().saveNow();
		ShowRestartPrompt(controller);
	}, enabled->lifetime());
	const auto safe = toggle(u"plugins_safe_mode"_q, tr::lng_netgram_plugins_manager_safe());
	safe->toggledChanges() | rpl::filter([](bool value) {
		return value != Netgram::Bool(u"plugins_safe_mode"_q);
	}) | rpl::on_next([](bool value) {
		Netgram::Config::Instance().setBool(u"plugins_safe_mode"_q, value);
		Netgram::Config::Instance().saveNow();
	}, safe->lifetime());
	const auto unknownStates = std::make_shared<rpl::event_stream<bool>>();
	const auto unknown = builder.addButton({
		.id = u"netgram/plugins_unknown_sources"_q,
		.title = tr::lng_netgram_plugins_manager_unknown(),
		.st = &st::settingsButtonNoIcon,
		.toggled = unknownStates->events_starting_with(Netgram::Bool(u"plugins_unknown_sources"_q)),
	});
	unknown->toggledChanges() | rpl::filter([](bool value) {
		return value != Netgram::Bool(u"plugins_unknown_sources"_q);
	}) | rpl::on_next([=](bool value) {
		if (!value) {
			Netgram::Config::Instance().setBool(u"plugins_unknown_sources"_q, false);
			return;
		}
		Netgram::Plugins::ShowUnknownSourcesWarning(controller, [=](bool allowed) {
			Netgram::Config::Instance().setBool(u"plugins_unknown_sources"_q, allowed);
			Netgram::Config::Instance().saveNow();
			unknownStates->fire_copy(allowed);
		});
	}, unknown->lifetime());
	builder.addButton({
		.id = u"netgram/plugins_install"_q,
		.title = tr::lng_netgram_plugins_manager_install(),
		.icon = { &st::menuIconDownload },
		.onClick = [=] {
			if (Netgram::Plugins::Started()) {
				Netgram::Plugins::ChooseAndInstall(controller);
			} else {
				controller->showToast(tr::lng_netgram_plugins_manager_not_running(tr::now));
			}
		},
	});
	builder.addButton({
		.id = u"netgram/plugins_export"_q,
		.title = tr::lng_netgram_plugins_manager_export(),
		.st = &st::settingsButtonNoIcon,
		.onClick = [=] {
			FileDialog::GetFolder(Core::App().getFileDialogParent(),
				tr::lng_netgram_plugins_manager_export(tr::now), QString(),
				[=](QString &&folder) { Netgram::Plugins::ExportAll(folder); });
		},
	});
	if (!Netgram::Plugins::RuntimeError().isEmpty()) {
		builder.addSubsectionTitle(rpl::single(Netgram::Plugins::RuntimeError()));
	}
	builder.addSkip();
	builder.add([=](const WidgetContext &ctx) {
		auto list = object_ptr<Ui::VerticalLayout>(ctx.container);
		Netgram::Plugins::FillPluginsList(list.data(), controller);
		return SectionBuilder::WidgetToAdd{ .widget = std::move(list) };
	});
});

} // namespace

PluginManager::PluginManager(QWidget *parent, not_null<Window::SessionController*> controller)
: Section(parent, controller) {
	const auto content = Ui::CreateChild<Ui::VerticalLayout>(this);
	build(content, kMeta.build);
	Ui::ResizeFitChild(this, content);
}

rpl::producer<QString> PluginManager::title() {
	return tr::lng_netgram_plugins_manager_title();
}

} // namespace Settings
