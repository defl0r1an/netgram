#include "netgram/plugins/plugin_trust.h"

#include <QtCore/QCryptographicHash>
#include <QtCore/QFile>

namespace Netgram::PluginTrust {

// This client has no centrally trusted channels. Files require an explicit
// local installation decision; importing another client's list would grant
// its publishers permission to run code in the user's account.
std::vector<Source> Sources() { return {}; }
std::vector<uint64> TrustedChannels() { return {}; }
DocumentId TrustedEmoji() { return 0; }
bool IsTrustedChannel(not_null<PeerData*> peer) { return false; }

QString Sha256(const QString &path) {
	auto file = QFile(path);
	if (!file.open(QIODevice::ReadOnly)) {
		return {};
	}
	auto hash = QCryptographicHash(QCryptographicHash::Sha256);
	return hash.addData(&file) ? QString::fromLatin1(hash.result().toHex()) : QString();
}

void Verify(not_null<Main::Session*> session, const QString &path, Fn<void(bool)> done) {
	done(false);
}

void VerifyForward(not_null<Main::Session*> session, not_null<ChannelData*> channel,
		MsgId id, DocumentId document, Fn<void(bool)> done) {
	done(false);
}

} // namespace Netgram::PluginTrust
