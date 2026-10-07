// This is the source code of AyuGram for Desktop.
//
// We do not and cannot prevent the use of our code,
// but be respectful and credit the original author.
//
// Copyright @Radolyn, 2026
#include "ayu/ui/components/avatar_corners_preview.h"

#include "data/data_peer.h"
#include "data/data_user.h"
#include "lang/lang_keys.h"
#include "main/main_session.h"
#include "styles/style_dialogs.h"
#include "styles/style_settings.h"
#include "ui/painter.h"
#include "window/window_session_controller.h"

// netgram: the preview shows the user's own profile picture, so the
// settings page does not resolve or open any third-party channel.
AvatarCornersPreview::AvatarCornersPreview(
	QWidget *parent,
	not_null<Window::SessionController*> controller)
: RpWidget(parent)
, _peer(controller->session().user()) {
	const auto &row = st::defaultDialogRow;
	setFixedHeight(row.height);
	_peer->loadUserpic();
	_peer->session().downloaderTaskFinished(
	) | rpl::on_next([=] {
		update();
	}, lifetime());
}

void AvatarCornersPreview::paintEvent(QPaintEvent *e) {
	auto p = Painter(this);

	const auto &row = st::defaultDialogRow;
	const auto photoSize = row.photoSize;
	const auto xShift = st::settingsButtonNoIcon.padding.left()
		- row.padding.left();
	const auto userpicX = row.padding.left() + xShift;
	const auto userpicY = (height() - photoSize) / 2;

	p.fillRect(rect(), st::windowBg);

	_peer->paintUserpicLeft(
		p, _userpicView, userpicX, userpicY, width(), photoSize);

	const auto nameText = st::semiboldFont->elided(
		_peer->name(),
		std::max(width() - row.nameLeft - xShift - row.padding.right(), 0));
	p.setPen(st::dialogsNameFg);
	p.setFont(st::semiboldFont);
	p.drawText(row.nameLeft + xShift, row.nameTop + st::semiboldFont->ascent, nameText);

	p.setPen(st::dialogsTextFg);
	p.setFont(st::dialogsTextFont);
	p.drawText(
		row.textLeft + xShift,
		row.textTop + st::dialogsTextFont->ascent,
		tr::lng_netgram_preview_channel_text(tr::now));
}
