SKILLS_DIR := $(HOME)/.claude/skills
DIST_DIR := dist

SKILLS := $(patsubst %/SKILL.md,%,$(wildcard */SKILL.md))

# Restrict to a single skill with: make install SKILL=token-audit
ifdef SKILL
SKILLS := $(SKILL)
endif

.PHONY: zip install clean

zip:
	@mkdir -p $(DIST_DIR)
	@for s in $(SKILLS); do \
		rm -f $(DIST_DIR)/$$s.zip; \
		(cd $$s && zip -rq ../$(DIST_DIR)/$$s.zip . -x '*.DS_Store'); \
		echo "Packaged $$s -> $(DIST_DIR)/$$s.zip"; \
	done

install: zip
	@for s in $(SKILLS); do \
		rm -rf $(SKILLS_DIR)/$$s; \
		mkdir -p $(SKILLS_DIR)/$$s; \
		unzip -q -o $(DIST_DIR)/$$s.zip -d $(SKILLS_DIR)/$$s; \
		echo "Installed $$s -> $(SKILLS_DIR)/$$s"; \
	done

clean:
	rm -rf $(DIST_DIR)
