#
#   Copyright 2015  Xebia Nederland B.V.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

ifeq ($(strip $(PROJECT)),)
  NAME=$(shell basename $(CURDIR))
else
  NAME=$(PROJECT)
endif

RELEASE_SUPPORT := $(shell dirname $(abspath $(lastword $(MAKEFILE_LIST))))/.make-release-support

ifeq ($(strip $(DOCKER_REGISTRY_HOST)),)
  DOCKER_REGISTRY_HOST = nexus.engageska-portugal.pt
endif

ifeq ($(strip $(DOCKER_REGISTRY_USER)),)
  DOCKER_REGISTRY_USER = ska-docker
endif

IMAGE=$(DOCKER_REGISTRY_HOST)/$(DOCKER_REGISTRY_USER)/$(NAME)

#VERSION = release version + git sha
VERSION=$(shell . $(RELEASE_SUPPORT) ; getVersion)

#BASE_VERSION
BASE_VERSION=$(shell . $(RELEASE_SUPPORT) ; getRelease)

#TAG = project name + release version
TAG=$(shell . $(RELEASE_SUPPORT); getTag)

#DEFAULT_TAG = image name + BASE_VERSION
DEFAULT_TAG=$(IMAGE):$(BASE_VERSION)


SHELL=/bin/bash

DOCKER_BUILD_CONTEXT=.
DOCKER_FILE_PATH=Dockerfile

.PHONY: pre-build docker-build post-build build release patch-release minor-release major-release tag check-status check-release showver \
	push pre-push do-push post-push

build: pre-build docker-build post-build  ## build the application image

pre-build:

post-build:

pre-push:

post-push:

docker-build: .release
	@echo "Building image: $(IMAGE):$(VERSION)"
	docker build $(DOCKER_BUILD_ARGS) -t $(IMAGE):$(VERSION) $(DOCKER_BUILD_CONTEXT) -f $(DOCKER_FILE_PATH) --build-arg DOCKER_REGISTRY_HOST=$(DOCKER_REGISTRY_HOST) --build-arg DOCKER_REGISTRY_USER=$(DOCKER_REGISTRY_USER)
	@DOCKER_MAJOR=$(shell docker -v | sed -e 's/.*version //' -e 's/,.*//' | cut -d\. -f1) ; \
	DOCKER_MINOR=$(shell docker -v | sed -e 's/.*version //' -e 's/,.*//' | cut -d\. -f2) ; \
	if [ $$DOCKER_MAJOR -eq 1 ] && [ $$DOCKER_MINOR -lt 10 ] ; then \
		echo docker tag -f $(IMAGE):$(VERSION) $(IMAGE):latest ;\
		docker tag -f $(IMAGE):$(VERSION) $(IMAGE):latest ;\
	else \
		echo docker tag $(IMAGE):$(VERSION) $(IMAGE):latest ;\
		docker tag $(IMAGE):$(VERSION) $(IMAGE):latest ; \
	fi

release: check-status check-release build push

push: pre-push do-push post-push  ## push the image to the Docker registry

do-push: ## Push the image tagged as $(IMAGE):$(VERSION) and $(DEFAULT_TAG)
	@echo -e "Tagging: $(IMAGE):$(VERSION) -> $(DEFAULT_TAG)"
	docker tag $(IMAGE):$(VERSION) $(DEFAULT_TAG)
	@echo -e "Pushing: $(IMAGE):$(VERSION)"
	docker push $(IMAGE):$(VERSION)
	@echo -e "Pushing: $(DEFAULT_TAG)"
	docker push $(DEFAULT_TAG)

tag_latest: do-push ## Tag the images as latest
	@echo "Tagging: $(DEFAULT_TAG) -> $(IMAGE):latest"
	@docker tag $(DEFAULT_TAG) $(IMAGE):latest

push_latest: tag_latest ## Push the image tagged as :latest
	@echo "Pushing: $(IMAGE):latest"
	@docker push $(IMAGE):latest

snapshot: build push

showver: .release
	@. $(RELEASE_SUPPORT); getVersion

bump-patch-release: VERSION := $(shell . $(RELEASE_SUPPORT); nextPatchLevel)
bump-patch-release: .release tag

bump-minor-release: VERSION := $(shell . $(RELEASE_SUPPORT); nextMinorLevel)
bump-minor-release: .release tag

bump-major-release: VERSION := $(shell . $(RELEASE_SUPPORT); nextMajorLevel)
bump-major-release: .release tag

patch-release: tag-patch-release release
	@echo $(VERSION)

minor-release: tag-minor-release release
	@echo $(VERSION)

major-release: tag-major-release release
	@echo $(VERSION)

tag: TAG=$(shell . $(RELEASE_SUPPORT); getTag $(VERSION))
tag: check-status
#	@. $(RELEASE_SUPPORT) ; ! tagExists $(TAG) || (echo "ERROR: tag $(TAG) for version $(VERSION) already tagged in git" >&2 && exit 1) ;
	@. $(RELEASE_SUPPORT) ; setRelease $(VERSION)
#	git add .
#	git commit -m "bumped to version $(VERSION)" ;
#	git tag $(TAG) ;
#	@ if [ -n "$(shell git remote -v)" ] ; then git push --tags ; else echo 'no remote to push tags to' ; fi

check-status:
	@. $(RELEASE_SUPPORT) ; ! hasChanges || (echo "ERROR: there are still outstanding changes" >&2 && exit 1) ;

check-release: .release
	@. $(RELEASE_SUPPORT) ; tagExists $(TAG) || (echo "ERROR: version not yet tagged in git. make [minor,major,patch]-release." >&2 && exit 1) ;
	@. $(RELEASE_SUPPORT) ; ! differsFromRelease $(TAG) || (echo "ERROR: current directory differs from tagged $(TAG). make [minor,major,patch]-release." ; exit 1)
