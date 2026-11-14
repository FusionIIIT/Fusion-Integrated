import React from 'react';
import { Route, Switch } from 'react-router-dom';
import HrEisRoutes from './routes';

const HrEisModule = () => (
    <Switch>
        <Route path="/hr_eis" component={HrEisRoutes} />
    </Switch>
);

export default HrEisModule;
