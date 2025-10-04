<template>
	<div>
		<div class="mb-4 flex items-center justify-between">
			<div class="flex items-center space-x-2">
				<TextInput
					placeholder="Search"
					class="max-w-[20rem]"
					:debounce="500"
					v-model="searchQuery"
				>
					<template #prefix>
						<lucide-search class="h-4 w-4 text-gray-500" />
					</template>
				</TextInput>
				<ObjectListFilters
					v-if="filterControls.length"
					:filterControls="filterControls"
					@update:filter="onFilterControlChange"
				/>
			</div>
			<div class="flex items-center space-x-2">
				<Button label="Refresh" @click="$list.reload()" :loading="isLoading">
					<template #icon>
						<lucide-refresh-ccw class="h-4 w-4" />
					</template>
				</Button>
				<Button
					label="New Bench Group"
					variant="solid"
					@click="$router.push({ name: 'New Release Group' })"
				>
					<template #prefix>
						<lucide-plus class="h-4 w-4" />
					</template>
				</Button>
			</div>
		</div>

		<div
			v-if="filteredGroups.length > 0"
			class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
		>
			<BenchGroupCard
				v-for="group in filteredGroups"
				:key="group.name"
				:group="group"
			/>
		</div>

		<div v-else-if="isLoading" class="py-8 text-center text-sm text-gray-500">
			Loading...
		</div>

		<div v-else class="py-8 text-center text-sm text-gray-500">
			No bench groups found
		</div>

		<div class="mt-4 text-center" v-if="$list?.next && $list?.hasNextPage">
			<Button @click="$list.next()" :loading="isLoading"> Load more </Button>
		</div>
	</div>
</template>

<script>
import { reactive } from 'vue';
import BenchGroupCard from './BenchGroupCard.vue';
import ObjectListFilters from '../ObjectListFilters.vue';
import { TextInput, Button } from 'frappe-ui';

export default {
	name: 'BenchGroupGridList',
	components: {
		BenchGroupCard,
		ObjectListFilters,
		TextInput,
		Button,
	},
	props: {
		options: {
			type: Object,
			required: true,
		},
	},
	data() {
		return {
			searchQuery: '',
		};
	},
	watch: {
		searchQuery(value) {
			if (this.options.searchField && this.$list?.list) {
				if (value) {
					this.$list.update({
						filters: {
							...this.$list.filters,
							[this.options.searchField]: ['like', `%${value.toLowerCase()}%`],
						},
						start: 0,
						pageLength: this.options.pageLength || 20,
					});
				} else {
					this.$list.update({
						filters: {
							...this.$list.filters,
							[this.options.searchField]: undefined,
						},
						start: 0,
						pageLength: this.options.pageLength || 20,
					});
				}
				this.$list.reload();
			}
		},
	},
	resources: {
		list() {
			if (this.options.data) return;
			if (this.options.list) return;

			return {
				type: 'list',
				cache: ['BenchGroupGridList', this.options.doctype, this.options.filters],
				doctype: this.options.doctype,
				pageLength: this.options.pageLength || 20,
				fields: [
					'name',
					'title',
					'active_benches',
					'version',
					'site_count',
					{ apps: ['app'] },
				],
				filters: this.options.filters || {},
				orderBy: this.options.orderBy,
				auto: true,
			};
		},
	},
	mounted() {
		if (this.options.data) return;
		if (this.options.list) {
			const resource = this.$list.list || this.$list;
			if (!resource.fetched && !resource.loading && this.$list.auto != false) {
				resource.fetch();
			}
		}
	},
	computed: {
		$list() {
			if (this.$resources.list) return this.$resources.list;
			if (this.options.list) {
				if (typeof this.options.list === 'function') {
					return this.options.list(this.options.context);
				}
				return this.options.list;
			}
		},
		filteredGroups() {
			const groups = this.$list?.data || [];
			if (!this.searchQuery || this.options.searchField) return groups;

			const query = this.searchQuery.toLowerCase();
			return groups.filter((group) => {
				return (
					group.title?.toLowerCase().includes(query) ||
					group.version?.toLowerCase().includes(query) ||
					group.apps?.some((app) => app.app.toLowerCase().includes(query))
				);
			});
		},
		isLoading() {
			return this.$list?.list?.loading || this.$list?.loading;
		},
		filterControls() {
			if (!this.options.filterControls) return [];
			let controls = this.options.filterControls(this.context);
			return controls
				.filter((control) => control.fieldname)
				.map((control) => {
					return reactive({ ...control, value: control.default || undefined });
				});
		},
		context() {
			return {
				...this.options.context,
				listResource: this.$list,
			};
		},
	},
	methods: {
		onFilterControlChange(control) {
			let filters = { ...this.$list.filters };
			for (let c of this.filterControls) {
				filters[c.fieldname] = c.value;
			}
			this.$list.update({
				filters,
				start: 0,
				pageLength: this.options.pageLength || 20,
			});
			this.$list.reload();
		},
	},
};
</script>
