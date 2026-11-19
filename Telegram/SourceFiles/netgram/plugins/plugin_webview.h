#pragma once

namespace Netgram::PluginWeb {

void Open(const QString &payload);
void Eval(int64 id, const QString &script);
void Close(int64 id);
void CloseOwner(const QString &owner);
void CloseAll();

} // namespace Netgram::PluginWeb
