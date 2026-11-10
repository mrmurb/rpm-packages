%global debug_package %{nil}
%global selinuxtype targeted
%global modulename linux_hello

Name:           linux-hello
Version:        0.1.1
Release:        1%{?dist}
Summary:        Windows Hello-style facial authentication for Linux using OpenCV and PAM

License:        Apache-2.0 AND MIT
URL:            https://github.com/kennycoder/linux-hello
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz
Source1:        %{modulename}.te
Source2:        %{modulename}.fc
Source3:        %{name}-selinux.conf
Source4:        %{name}-selinux-relabel

BuildRequires:  cargo
BuildRequires:  rust
BuildRequires:  gcc-c++
BuildRequires:  make
BuildRequires:  pkgconfig
BuildRequires:  opencv-devel
BuildRequires:  pam-devel
BuildRequires:  polkit-devel
BuildRequires:  clang-devel
BuildRequires:  cmake
BuildRequires:  extra-cmake-modules
BuildRequires:  qt6-qtbase-devel
BuildRequires:  qt6-qtdeclarative-devel
BuildRequires:  kf6-kcoreaddons-devel
BuildRequires:  kf6-kcmutils-devel
BuildRequires:  kf6-ki18n-devel
BuildRequires:  gettext
BuildRequires:  systemd-rpm-macros
BuildRequires:  selinux-policy-devel
BuildRequires:  bzip2

Requires:       authselect
Requires:       polkit
Requires:       hicolor-icon-theme
Requires:       kf6-kcmutils
Requires:       kf6-kirigami
Requires:       kf6-kirigami-addons
Requires:       (%{name}-selinux if selinux-policy-%{selinuxtype})
Suggests:       plasma-systemsettings

%description
Linux Hello brings facial recognition authentication to Linux desktops using
standard webcams and infrared cameras, providing a Windows Hello-like
experience for sudo, login managers, and lock screens.

%package selinux
Summary:        SELinux policy for %{name}
License:        GPL-2.0-or-later
BuildArch:      noarch
Requires:       selinux-policy-%{selinuxtype}
Requires:       policycoreutils
Requires(post): selinux-policy-%{selinuxtype}

%description selinux
SELinux policy allowing display-manager PAM helpers to access the
Linux-Hello daemon socket.

%prep
%autosetup -n %{name}-%{version}

%build
%make_build build REQUIRE_KCM=1

mkdir -p selinux
cp -p %{SOURCE1} selinux/%{modulename}.te
cp -p %{SOURCE2} selinux/%{modulename}.fc
make -C selinux -f %{_datadir}/selinux/devel/Makefile %{modulename}.pp
bzip2 -9 selinux/%{modulename}.pp

%install
%make_install PREFIX=/usr
install -D -m 0644 selinux/%{modulename}.pp.bz2 %{buildroot}%{_datadir}/selinux/packages/%{selinuxtype}/%{modulename}.pp.bz2
install -D -m 0644 %{SOURCE3} %{buildroot}%{_unitdir}/linux-hello.service.d/10-selinux.conf
install -D -m 0755 %{SOURCE4} %{buildroot}%{_libexecdir}/linux-hello-selinux-relabel

%post
%systemd_post linux-hello.service

%preun
%systemd_preun linux-hello.service
if [ $1 -eq 0 ]; then
    # Package removal: rollback PAM changes if configured via authselect
    if [ -x %{_bindir}/linux-hello ]; then
        %{_bindir}/linux-hello disable 2>/dev/null || true
    fi
fi

%postun
%systemd_postun_with_restart linux-hello.service

%pre selinux
%selinux_relabel_pre -s %{selinuxtype}

%post selinux
%selinux_modules_install -s %{selinuxtype} %{_datadir}/selinux/packages/%{selinuxtype}/%{modulename}.pp.bz2
%selinux_relabel_post -s %{selinuxtype}
/usr/bin/systemctl daemon-reload >/dev/null 2>&1 || true
/usr/bin/restorecon /run/linux-hello.sock >/dev/null 2>&1 || true

%posttrans selinux
%selinux_relabel_post -s %{selinuxtype}

%postun selinux
if [ $1 -eq 0 ]; then
    %selinux_modules_uninstall -s %{selinuxtype} %{modulename}
    %selinux_relabel_post -s %{selinuxtype}
fi
/usr/bin/systemctl daemon-reload >/dev/null 2>&1 || true

%files
%license LICENSE
%doc README.md
%{_bindir}/linux-hello
%{_bindir}/linux-hellod
%{_bindir}/linux-hello-gui
%{_libdir}/security/pam_linux_hello.so
%{_libdir}/qt6/plugins/plasma/kcms/systemsettings/kcm_linuxhello.so
%{_datadir}/applications/linux-hello-gui.desktop
%{_datadir}/applications/kcm_linuxhello.desktop
%{_datadir}/icons/hicolor/scalable/apps/linux-hello.svg
%{_datadir}/polkit-1/actions/org.linuxhello.pkexec.policy
%{_datadir}/linux-hello/
%{_unitdir}/linux-hello.service
%dir %{_localstatedir}/lib/linux-hello
%dir %{_localstatedir}/lib/linux-hello/models

%files selinux
%{_datadir}/selinux/packages/%{selinuxtype}/%{modulename}.pp.*
%{_unitdir}/linux-hello.service.d/10-selinux.conf
%{_libexecdir}/linux-hello-selinux-relabel
%ghost %verify(not md5 size mode mtime) %{_sharedstatedir}/selinux/%{selinuxtype}/active/modules/200/%{modulename}

%changelog
* Tue Nov 10 2026 Max Enelund <max@ig4.se> - 0.1.1-1
- Initial Copr package based on upstream spec
- Add SELinux policy subpackage with a dedicated socket type and relabel helper

* Sun Oct 25 2026 Nikolai <kennycoder@users.noreply.github.com> - 0.1.0-1
- Initial RPM release
