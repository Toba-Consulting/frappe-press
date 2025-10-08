<template>
	<div class="sticky top-0 z-10 bg-white">
		<Header>
			<div class="w-full">
				<!-- Back link -->
				<router-link
					:to="object.list.route"
					class="mb-3 flex items-center text-sm text-gray-600 hover:text-gray-900"
				>
					<lucide-arrow-left class="mr-1.5 h-3.5 w-3.5" />
					Back to {{ object.list.title }}
				</router-link>

				<!-- Title row with badge and actions -->
				<div class="flex items-center justify-between">
					<div class="flex items-center space-x-3">
						<h1 class="text-2xl font-semibold text-gray-900">
							{{ title }}
						</h1>
						<Badge
							v-if="$resources.document?.doc && badge"
							v-bind="badge"
						/>
					</div>
					<div
						class="flex items-center space-x-2"
						v-if="$resources.document?.doc"
					>
						<ActionButton
							v-for="button in actions"
							v-bind="button"
							:key="button.label"
						/>
					</div>
				</div>
			</div>
		</Header>

		<!-- Tabs Section -->
		<div class="border-b bg-white px-5" v-if="!$resources.document.get.error && $resources.document.get.fetched">
			<FTabs v-if="visibleTabs?.length" v-model="currentTab" :tabs="visibleTabs">
				<template #default>
					<!-- Empty template to prevent default tab panel rendering -->
				</template>
			</FTabs>
		</div>
	</div>

	<div>
		<div
			v-if="$resources.document.get.error"
			class="mx-auto mt-60 w-fit rounded border border-dashed px-12 py-8 text-center text-gray-600"
		>
			<lucide-alert-triangle class="mx-auto mb-4 h-6 w-6 text-red-600" />
			<ErrorMessage :message="$resources.document.get.error" />
		</div>
		<div v-else-if="$resources.document.get.fetched">
			<router-view
				v-if="$resources.document?.doc"
				:document="$resources.document"
				:tab="activeTab"
			/>
		</div>
	</div>
</template>

<script>
import Header from '../components/Header.vue';
import ActionButton from '../components/ActionButton.vue';
import { Breadcrumbs, Tabs } from 'frappe-ui';
import { getObject } from '../objects';

let subscribed = {};

export default {
	name: 'DetailPage',
	props: {
		id: String,
		objectType: {
			type: String,
			required: true,
		},
		name: {
			type: String,
			required: true,
		},
	},
	components: {
		Header,
		ActionButton,
		FBreadcrumbs: Breadcrumbs,
		FTabs: Tabs,
	},
	resources: {
		document() {
			return {
				type: 'document',
				doctype: this.object.doctype,
				name: this.name,
				whitelistedMethods: this.object.whitelistedMethods || {},
				onError(error) {
					for (let message of error?.messages || []) {
						if (message.redirect) {
							window.location.href = message.redirect;
							return;
						}
					}
				},
			};
		},
	},
	mounted() {
		if (!subscribed[`${this.object.doctype}:${this.name}`]) {
			this.$socket.emit('doc_subscribe', this.object.doctype, this.name);
			subscribed[`${this.object.doctype}:${this.name}`] = true;
		}
		this.$socket.on('doc_update', (data) => {
			if (data.doctype === this.object.doctype && data.name === this.name) {
				this.$resources.document.reload();
			}
		});
	},
	beforeUnmount() {
		let doctype = this.object.doctype;
		if (subscribed[`${doctype}:${this.name}`]) {
			this.$socket.emit('doc_unsubscribe', doctype, this.name);
			subscribed[`${doctype}:${this.name}`] = false;
		}
	},
	computed: {
		object() {
			return getObject(this.objectType);
		},
		tabs() {
			return this.object.detail.tabs.filter((tab) => {
				if (tab.condition) {
					return tab.condition({
						documentResource: this.$resources.document,
					});
				}
				return true;
			});
		},
		visibleTabs() {
			return this.tabs.filter((tab) =>
				tab.condition ? tab.condition({ doc: this.$resources.document?.doc }) : true,
			);
		},
		currentTab: {
			get() {
				for (let tab of this.visibleTabs) {
					let tabRouteName = tab.routeName || tab.route.name;
					if (
						this.$route.name === tabRouteName ||
						tab.childrenRoutes?.includes(this.$route.name)
					) {
						return this.visibleTabs.indexOf(tab);
					}
				}
				return 0;
			},
			set(val) {
				let tab = this.visibleTabs[val];
				let tabRouteName = tab.routeName || tab.route.name;
				this.$router.push({ name: tabRouteName });
			},
		},
		activeTab() {
			return this.visibleTabs[this.currentTab];
		},
		title() {
			let doc = this.$resources.document?.doc;
			return doc ? doc[this.object.detail.titleField || 'name'] : this.name;
		},
		badge() {
			if (this.object.detail.statusBadge) {
				return this.object.detail.statusBadge({
					documentResource: this.$resources.document,
				});
			}
			return null;
		},
		actions() {
			if (this.object.detail.actions && this.$resources.document?.doc) {
				let actions = this.object.detail.actions({
					documentResource: this.$resources.document,
				});
				return actions.filter((action) => {
					if (action.condition) {
						return action.condition({
							documentResource: this.$resources.document,
						});
					}
					return true;
				});
			}
			return [];
		},
		breadcrumbs() {
			let items = [
				{ label: this.object.list.title, route: this.object.list.route },
				{
					label: this.title,
					route: {
						name: `${this.object.doctype} Detail`,
						params: { name: this.name },
					},
				},
			];
			if (this.object.detail.breadcrumbs && this.$resources.document?.doc) {
				let result = this.object.detail.breadcrumbs({
					documentResource: this.$resources.document,
					items,
				});
				if (Array.isArray(result)) {
					items = result;
				}
			}

			// add ellipsis if breadcrumbs too long
			for (let i = 0; i < items.length; i++) {
				if (items[i].label.length > 30 && i !== items.length - 1) {
					items[i].label = items[i].label.slice(0, 30) + '...';
				}
			}

			return items;
		},
	},
};
</script>
<style scoped>
:deep(button[role='tab']) {
	white-space: nowrap;
}
</style>
