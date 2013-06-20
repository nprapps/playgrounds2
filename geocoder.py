    def geocode(self):
        '''
        Geocodes an instance of a model.
        '''
        g = geocoders.GoogleV3()
        address = self.address
        city = self.city
        state = self.state
        zip_code = self.zip_code
        place, (lat, lng) = g.geocode('{0} {1} {3} {3}').format(address, city, state, zip_code)
        print '%.5f, %.5f' % (lat, lng)