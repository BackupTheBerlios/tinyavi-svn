%{!?python_site: %define python_site %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib(0)")}

Name:           tinyavi
Version:        0.2.0
Release:        1%{?dist}
Summary:        An easy video converter for portable devices
Group:          Applications/Multimedia
License:        GPLv3+
URL:            http://tinyavi.berlios.de/
Source0:        http://download.berlios.de/tinyavi/tinyavi-%{version}.tar.bz2
BuildArch:      noarch
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root
BuildRequires:  python
BuildRequires:  desktop-file-utils
Requires:       python pygtk2 pygtk2-libglade mplayer mencoder
Requires:       desktop-file-utils

%description
TinyAVI is a set of two tools (one command-line, one GUI) which can convert
video files to a format suitable for (some) portable devices.

%prep
%setup -q

%build
# nothing to do :)

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --root $RPM_BUILD_ROOT
%find_lang %{name}

%clean
rm -rf $RPM_BUILD_ROOT

%files -f %{name}.lang
%defattr(-,root,root,-)
%doc CHANGELOG COPYING README TRANSLATORS
%{python_site}/%{name}/*
%{_bindir}/tavi
%{_bindir}/tavi-gui
%{_datadir}/applications/*.desktop
%{_datadir}/pixmaps/*
%{_datadir}/%{name}/*

%post
update-desktop-database -q

%postun
update-desktop-database -q

%changelog
* Wed Mar 19 2008 Andrew Zabolotny <zap@homelink.ru> - 0.1.0-1
- Wrote the spec file using the spec file from Sonata as template :)
