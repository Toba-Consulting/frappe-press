<template>
	<div>
		<slot :navigation="navigation" />
	</div>
</template>
<script>
import { h } from 'vue';
import DoorOpen from '~icons/lucide/door-open';
import PanelTopInactive from '~icons/lucide/panel-top-inactive';
import Package from '~icons/lucide/package';
import Boxes from '~icons/lucide/boxes';
import Server from '~icons/lucide/server';
import WalletCards from '~icons/lucide/wallet-cards';
import Settings from '~icons/lucide/settings';
import App from '~icons/lucide/layout-grid';
import DatabaseZap from '~icons/lucide/database-zap';
import Activity from '~icons/lucide/activity';
import Logs from '~icons/lucide/scroll-text';
import Globe from '~icons/lucide/globe';
import Shield from '~icons/lucide/shield';
import NotificationIcon from '@/components/icons/navigate_item/NotificationIcon.vue';
import SiteIcon from '@/components/icons/navigate_item/SiteIcon.vue';
import BenchIcon from '@/components/icons/navigate_item/BenchIcon.vue';
import BenchGroupIcon from '@/components/icons/navigate_item/BenchGroupIcon.vue';
import MarketplaceIcon from '@/components/icons/navigate_item/MarketplaceIcon.vue';
import DevIcon from '@/components/icons/navigate_item/DevIcon.vue';
import BillingIcon from '@/components/icons/navigate_item/BillingIcon.vue';
import PartnershipIcon from '@/components/icons/navigate_item/PartnershipIcon.vue';
import SettingIcon from '@/components/icons/navigate_item/SettingIcon.vue';
import Code from '~icons/lucide/code';
import FileSearch from '~icons/lucide/file-search';
import { unreadNotificationsCount } from '../data/notifications';

export default {
	name: 'NavigationItems',
	computed: {
		navigation() {
			if (!this.$team?.doc) return [];

			const routeName = this.$route?.name || '';
			const onboardingComplete = this.$team.doc.onboarding.complete;
			const isSaasUser = this.$team.doc.is_saas_user;
			const enforce2FA = Boolean(
				!this.$team.doc.is_desk_user &&
					this.$team.doc.enforce_2fa &&
					!this.$team.doc.user_info?.is_2fa_enabled,
			);

			return [
				{
					name: 'Welcome',
					icon: () => h(DoorOpen),
					route: '/welcome',
					isActive: routeName === 'Welcome',
					condition: !onboardingComplete,
					color: '#9C27B0',
				},
				{
					name: 'Notifications',
					icon: () => h(NotificationIcon),
					route: '/notifications',
					isActive: routeName === 'Press Notification List',
					condition: onboardingComplete && !isSaasUser,
					badge: () => {
						if (unreadNotificationsCount.data > 0) {
							return h(
								'span',
								{
									class: '!ml-auto px-1.5 py-0.5 text-xs text-gray-600',
								},
								unreadNotificationsCount.data > 99
									? '99+'
									: unreadNotificationsCount.data,
							);
						}
					},
					disabled: enforce2FA,
					color: '#FF6B35',
				},
				{
					name: 'Sites',
					icon: () => h(SiteIcon),
					route: '/sites',
					isActive:
						['Site List', 'Site Detail', 'New Site'].includes(routeName) ||
						routeName.startsWith('Site Detail'),
					disabled: enforce2FA,
					color: '#00D68F',
				},
				{
					name: 'Benches',
					icon: () => h(BenchIcon),
					route: '/benches',
					isActive: routeName.startsWith('Bench'),
					condition: this.$team.doc?.is_desk_user,
					disabled: !onboardingComplete || enforce2FA,
					color: '#2196F3',
				},
				{
					name: 'Bench Groups',
					icon: () => h(BenchGroupIcon),
					route: onboardingComplete ? '/groups' : '/enable-bench-groups',
					isActive:
						[
							'Release Group List',
							'Release Group Detail',
							'New Release Group',
							'Release Group New Site',
							'Deploy Candidate',
						].includes(routeName) ||
						routeName.startsWith('Release Group Detail') ||
						routeName === 'Enable Bench Groups',
					disabled: enforce2FA,
					color: '#9C27B0',
				},
				/*{
					name: 'Servers',
					icon: () => h(Server),
					route: onboardingComplete ? '/servers' : '/enable-servers',
					isActive:
						['New Server'].includes(routeName) ||
						routeName.startsWith('Server') ||
						routeName === 'Enable Servers',
					disabled: enforce2FA,
				},*/
				{
					name: 'Marketplace',
					icon: () => h(MarketplaceIcon),
					route: '/apps',
					isActive: routeName.startsWith('Marketplace'),
					condition:
						this.$team.doc?.is_desk_user ||
						(!!this.$team.doc.is_developer && this.$session.hasAppsAccess),
					disabled: enforce2FA,
					color: '#FFC107',
				},
				{
					name: 'Dev Tools',
					icon: () => h(DevIcon),
					route: '/devtools',
					condition: onboardingComplete && !isSaasUser,
					disabled: enforce2FA,
					children: [
						{
							name: 'Log Browser',
							icon: () => h(Logs),
							route: '/log-browser',
							isActive: routeName === 'Log Browser',
						},
						{
							name: 'DB Analyzer',
							icon: () => h(Activity),
							route: '/database-analyzer',
							isActive: routeName === 'DB Analyzer',
						},
						{
							name: 'SQL Playground',
							icon: () => h(DatabaseZap),
							route: '/sql-playground',
							isActive: routeName === 'SQL Playground',
						},
						/*
						{
							name: 'Binlog Browser',
							icon: () => h(FileSearch),
							route: '/binlog-browser',
							isActive: routeName === 'Binlog Browser',
						},
						*/
					].filter((item) => item.condition ?? true),
					isActive: [
						'SQL Playground',
						'DB Analyzer',
						'Log Browser',
						'Binlog Browser',
					].includes(routeName),
					disabled: enforce2FA,
					color: '#FF6B35',
				},
				{
					name: 'Billing',
					icon: () => h(BillingIcon),
					route: '/billing',
					isActive: routeName.startsWith('Billing'),
					condition:
						this.$team.doc?.is_desk_user || this.$session.hasBillingAccess,
					disabled: enforce2FA,
					color: '#00D68F',
				},
				{
					name: 'Partnership',
					icon: () => h(PartnershipIcon),
					route: '/partners',
					isActive: routeName === 'Partnership',
					/*condition: Boolean(this.$team.doc.erpnext_partner),*/
					disabled: enforce2FA,
					color: '#2196F3',
				},
				{
					name: 'Settings',
					icon: () => h(SettingIcon),
					route: '/settings',
					isActive: routeName.startsWith('Settings'),
					disabled: enforce2FA,
					color: '#9C27B0',
				},
				/*{
					name: 'Partner Admin',
					icon: () => h(Shield),
					route: '/partner-admin',
					isActive: routeName === 'Partner Admin',
					condition: Boolean(this.$team.doc.is_desk_user),
				},*/
			].filter((item) => item.condition ?? true);
		},
	},
	mounted() {
		this.$socket.emit('doctype_subscribe', 'Press Notification');
		this.$socket.on('press_notification', (data) => {
			if (data.team === this.$team.doc.name) {
				unreadNotificationsCount.setData((data) => data + 1);
			}
		});
	},
	unmounted() {
		this.$socket.off('press_notification');
	},
};
</script>
