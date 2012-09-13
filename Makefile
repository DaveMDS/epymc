#
# Simple and Stupid makefile for epymc
#
# make themes   -> will build the edje files
#
# make install-local  -> will install themes & .desktop file in the user
#                        share dir. Don't run this as root!
#

all:themes

themes:
	edje_cc -v data/themes/default/default.edc \
		-id data/themes/default/images/ \
		-fd data/themes/default/fonts/
	mv data/themes/default/default.edj data/themes/

clean:
	rm data/themes/default.edj

install-local:themes
	mkdir --parents ~/.local/share/applications/
	mkdir --parents ~/.local/share/icons/
	mkdir --parents ~/.config/epymc/themes/
	cp data/desktop/epymc.desktop epymc.desktop
	sed -i 's:Exec=.*:Exec=${CURDIR}/epymc.py:' epymc.desktop
	mv epymc.desktop ~/.local/share/applications/
	cp data/desktop/epymc.png ~/.local/share/icons/
	cp data/themes/default.edj ~/.config/epymc/themes/

uninstall-local:
	rm -f ~/.local/share/applications/epymc.desktop
	rm -f ~/.local/share/icons/epymc.png
	rm -f ~/.config/epymc/themes/default.edj


